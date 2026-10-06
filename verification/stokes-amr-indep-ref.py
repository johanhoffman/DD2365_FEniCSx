#!/usr/bin/env python3
"""Independent J_h reference for Stokes-AMR effectivity study.

(a) P2/P1 primal on fixed geometry at res=256
(b) P3/P2 primal on fixed geometry at res=128

Run:  conda run -n fenicsx-0.11 python stokes-amr-indep-ref.py
"""
import math
import numpy as np
from mpi4py import MPI
import ufl
import basix.ufl as bufl
from dolfinx.fem import functionspace, Function, form, assemble_scalar
from dolfinx.fem.petsc import NonlinearProblem
from petsc4py import PETSc

# ── Mesh helpers (canonical v6 with uniform_lc, canonical tag_boundaries v1) ─

import gmsh
from dolfinx.io import gmsh as gmshio
from dolfinx.mesh import locate_entities_boundary, meshtags

_ALPHA = 0.66
_N_SAMPLE = int(math.floor(math.sqrt(100.0 + 0.5)))


def _mshr_segments(r, L, H, resolution):
    R_enc = ((_N_SAMPLE - 1) / _N_SAMPLE) * math.sqrt(L ** 2 + H ** 2) / 2.0
    cs = 2.0 * R_enc / resolution
    return max(5, round(2.0 * math.pi * r / cs))


def gmsh_rect_minus_circles(L, H, circles, resolution, segments=32,
                             dist_min=None, dist_max=None, uniform_lc=False):
    lc = _ALPHA * math.sqrt(L ** 2 + H ** 2) / resolution
    eps = 1e-6 * max(L, H)
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.occ.addRectangle(0, 0, 0, L, H, tag=1)
    hole_tags = []
    segs_per_circle = []
    for cx, cy, r in circles:
        if segments == "mshr":
            n = _mshr_segments(r, L, H, resolution)
        elif isinstance(segments, int):
            n = segments
        else:
            raise ValueError(f"segments must be an int or 'mshr', got {segments!r}")
        segs_per_circle.append(n)
        pts = [
            gmsh.model.occ.addPoint(
                cx + r * math.cos(2 * math.pi * i / n),
                cy + r * math.sin(2 * math.pi * i / n),
                0,
            )
            for i in range(n)
        ]
        lines = [
            gmsh.model.occ.addLine(pts[i], pts[(i + 1) % n])
            for i in range(n)
        ]
        cl = gmsh.model.occ.addCurveLoop(lines)
        surf = gmsh.model.occ.addPlaneSurface([cl])
        hole_tags.append((2, surf))
    if hole_tags:
        gmsh.model.occ.cut([(2, 1)], hole_tags)
    gmsh.model.occ.synchronize()
    bg_fields = []
    for i, (cx, cy, r) in enumerate(circles):
        n = segs_per_circle[i]
        edge_len = 2 * r * math.sin(math.pi / n)
        c_curves = []
        for dim, tag in gmsh.model.getEntities(1):
            xmin, ymin, _, xmax, ymax, _ = gmsh.model.getBoundingBox(dim, tag)
            if xmin <= eps or xmax >= L - eps or ymin <= eps or ymax >= H - eps:
                continue
            bounds = gmsh.model.getParametrizationBounds(dim, tag)
            mid = float(np.array(bounds).mean())
            x, y, _ = gmsh.model.getValue(dim, tag, [mid])
            if abs(math.hypot(x - cx, y - cy) - r) < 0.15 * r:
                c_curves.append(tag)
        if not c_curves:
            continue
        dm_min = 0.0 if dist_min is None else dist_min
        dm_max = r / 2.0 if dist_max is None else dist_max
        d_id = 10 + 2 * i
        t_id = 11 + 2 * i
        gmsh.model.mesh.field.add("Distance", d_id)
        gmsh.model.mesh.field.setNumbers(d_id, "CurvesList", c_curves)
        gmsh.model.mesh.field.add("Threshold", t_id)
        gmsh.model.mesh.field.setNumber(t_id, "InField", d_id)
        gmsh.model.mesh.field.setNumber(t_id, "SizeMin", lc if uniform_lc else edge_len)
        gmsh.model.mesh.field.setNumber(t_id, "SizeMax", lc)
        gmsh.model.mesh.field.setNumber(t_id, "DistMin", dm_min)
        gmsh.model.mesh.field.setNumber(t_id, "DistMax", dm_max)
        bg_fields.append(t_id)
    if bg_fields:
        if len(bg_fields) == 1:
            gmsh.model.mesh.field.setAsBackgroundMesh(bg_fields[0])
        else:
            min_id = 10 + 2 * len(circles)
            gmsh.model.mesh.field.add("Min", min_id)
            gmsh.model.mesh.field.setNumbers(min_id, "FieldsList", bg_fields)
            gmsh.model.mesh.field.setAsBackgroundMesh(min_id)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.Algorithm", 5)
    surfaces = gmsh.model.getEntities(2)
    gmsh.model.addPhysicalGroup(2, [s[1] for s in surfaces], tag=10, name="domain")
    gmsh.model.mesh.generate(2)
    mesh_data = gmshio.model_to_mesh(gmsh.model, MPI.COMM_WORLD, rank=0, gdim=2)
    gmsh.finalize()
    return mesh_data.mesh, mesh_data.cell_tags


def tag_boundaries(msh, L, H, eps=None):
    if eps is None:
        eps = 1e-10 * max(L, H)
    fdim = msh.topology.dim - 1

    def on_left(x):   return x[0] < eps
    def on_right(x):  return x[0] > L - eps
    def on_lower(x):  return x[1] < eps
    def on_upper(x):  return x[1] > H - eps

    f_left  = locate_entities_boundary(msh, fdim, on_left)
    f_right = locate_entities_boundary(msh, fdim, on_right)
    f_lower = locate_entities_boundary(msh, fdim, on_lower)
    f_upper = locate_entities_boundary(msh, fdim, on_upper)
    known = np.concatenate([f_left, f_right, f_lower, f_upper])
    all_bdy = locate_entities_boundary(
        msh, fdim, lambda x: np.ones(x.shape[1], dtype=bool))
    f_obj = np.setdiff1d(all_bdy, known)
    indices = np.concatenate([f_left, f_right, f_lower, f_upper, f_obj]).astype(np.int32)
    values = np.concatenate([
        np.full(len(f_left),  1, dtype=np.int32),
        np.full(len(f_right), 2, dtype=np.int32),
        np.full(len(f_lower), 3, dtype=np.int32),
        np.full(len(f_upper), 4, dtype=np.int32),
        np.full(len(f_obj),   5, dtype=np.int32),
    ])
    order = np.argsort(indices)
    return meshtags(msh, fdim, indices[order], values[order])


# ── Primal Stokes solver ─────────────────────────────────────────────────────

def _solve_primal_stokes(msh, facet_tags, degree_v=2, degree_p=1, C=20, L=4, H=4):
    """Primal-only Stokes with symmetric Nitsche BCs; returns (J_h, n_cells)."""
    gdim = msh.geometry.dim
    Pv = bufl.element("Lagrange", msh.basix_cell(), degree_v, shape=(gdim,))
    Ps = bufl.element("Lagrange", msh.basix_cell(), degree_p)
    W  = functionspace(msh, bufl.mixed_element([Pv, Ps]))
    w  = Function(W)
    u_s, p_s = ufl.split(w)
    v, q     = ufl.TestFunctions(W)

    dx    = ufl.Measure("dx", domain=msh)
    ds    = ufl.Measure("ds", domain=msh, subdomain_data=facet_tags)
    h     = ufl.CellDiameter(msh)
    n     = ufl.FacetNormal(msh)
    x     = ufl.SpatialCoordinate(msh)
    gamma = C / h

    uin_v = ufl.as_vector([4.0 * x[1] * (H - x[1]) / (H * H), 0.0])
    g0    = ufl.as_vector([0.0, 0.0])

    def _N(u, p, vv, qq, g, ds_):
        t_u = ufl.dot(ufl.grad(u), n) - p * n
        t_v = ufl.dot(ufl.grad(vv), n) + qq * n
        return (
            - ufl.inner(t_u, vv) * ds_
            - ufl.inner(t_v, u - g) * ds_
            + gamma * ufl.inner(u - g, vv) * ds_
        )

    res = (
        - p_s * ufl.div(v) * dx
        + ufl.inner(ufl.grad(u_s), ufl.grad(v)) * dx
        + ufl.div(u_s) * q * dx
        + _N(u_s, p_s, v, q, uin_v, ds(1))
        + _N(u_s, p_s, v, q, g0,    ds(3))
        + _N(u_s, p_s, v, q, g0,    ds(4))
        + _N(u_s, p_s, v, q, g0,    ds(5))
    )
    _opts = {"snes_type": "newtonls", "snes_rtol": 1e-10, "snes_atol": 1e-12,
             "ksp_type": "preonly", "pc_type": "lu",
             "pc_factor_mat_solver_type": "mumps"}
    prob = NonlinearProblem(res, w,
                            petsc_options_prefix=f"p{degree_v}p{degree_p}_",
                            petsc_options=_opts)
    w = prob.solve()
    assert prob.solver.getConvergedReason() > 0, \
        f"P{degree_v}/P{degree_p} Newton did not converge"
    u_s, p_s = ufl.split(w)

    t_u_s = ufl.dot(ufl.grad(u_s), n) - p_s * n
    J_form = form(ufl.inner(-t_u_s + gamma * u_s,
                             ufl.as_vector([1.0, 0.0])) * ds(5))
    J_h = float(msh.comm.allreduce(assemble_scalar(J_form), op=MPI.SUM))
    n_cells = msh.topology.index_map(msh.topology.dim).size_global
    return J_h, n_cells


# ── Main ─────────────────────────────────────────────────────────────────────

L, H = 4, 4
circles = [(0.5, 0.5 * H, 0.2)]
C_nitsche = 20
segments_g = 128
uniform_lc_g = True

print("Stokes-AMR independent reference computations")
print("=" * 55)

# (a) P2/P1 res=256
print("\n(a) P2/P1 res=256 ...")
msh_a, _ = gmsh_rect_minus_circles(L, H, circles, 256,
                                    segments=segments_g, uniform_lc=uniform_lc_g)
ft_a = tag_boundaries(msh_a, L, H)
J_a, nc_a = _solve_primal_stokes(msh_a, ft_a, degree_v=2, degree_p=1,
                                  C=C_nitsche, L=L, H=H)
print(f"    cells={nc_a},  J_h={J_a:.10f}")

# (b) P3/P2 res=128
print("\n(b) P3/P2 res=128 ...")
msh_b, _ = gmsh_rect_minus_circles(L, H, circles, 128,
                                    segments=segments_g, uniform_lc=uniform_lc_g)
ft_b = tag_boundaries(msh_b, L, H)
J_b, nc_b = _solve_primal_stokes(msh_b, ft_b, degree_v=3, degree_p=2,
                                  C=C_nitsche, L=L, H=H)
print(f"    cells={nc_b},  J_h={J_b:.10f}")

# Comparison
rel = abs(J_a - J_b) / abs(J_a)
print(f"\nResults:")
print(f"  (a) P2/P1 res=256: {J_a:.10f}  (cells={nc_a})")
print(f"  (b) P3/P2 res=128: {J_b:.10f}  (cells={nc_b})")
print(f"  relative diff    : {rel:.2e}")
if rel < 1e-5:
    print(f"  => AGREE within 1e-5 — J_ref := {J_a:.10f}")
else:
    print(f"  => DO NOT AGREE — report both; do not set J_ref; STOP")
