import math
import numpy as np
import gmsh
from mpi4py import MPI
from dolfinx.io import gmsh as gmshio


_ALPHA = 0.66
# mshr numSamples=100 → N = floor(sqrt(100.5)) = 10 interior sample rows
_N_SAMPLE = int(math.floor(math.sqrt(100.0 + 0.5)))  # 10


def _mshr_segments(r, L, H, resolution):
    """Exact mshr auto-segment count for Circle(segments=0) in 2D.

    Source path:
      MeshGenerator.cpp: segment_granularity = 2*R_enc/resolution
      CSGGeometry.cpp:   estimate_bounding_sphere samples _N_SAMPLE×_N_SAMPLE
                         interior points; extreme corners dominate, giving
                         R_enc = ((N-1)/N) * sqrt(L²+H²) / 2
      CSGCGALDomain2D.cpp: num_segs = max(5, round(2π*r / segment_granularity))

    Verified predictions (no Steiner points since edge_len < cs_mshr):
      4×2 domain, r=0.2, resolution=32 → 10
      4×4 domain, r=0.2, resolution=32 →  8
    """
    R_enc = ((_N_SAMPLE - 1) / _N_SAMPLE) * math.sqrt(L ** 2 + H ** 2) / 2.0
    cs = 2.0 * R_enc / resolution
    return max(5, round(2.0 * math.pi * r / cs))


def gmsh_rect_minus_circles(L, H, circles, resolution, segments=32):
    """Rectangle [0,L]×[0,H] minus regular-polygon holes.

    Parameters
    ----------
    L, H : float
        Rectangle dimensions.
    circles : list of (cx, cy, r)
        Circle centres and radii.
    resolution : int
        Mesh density parameter.  Interior mesh size:
            lc = _ALPHA * sqrt(L² + H²) / resolution
    segments : int or "mshr"
        Number of polygon sides used to approximate each circle hole.
        Default 32.  Pass ``"mshr"`` to use the legacy mshr auto-segment
        rule (max(5, round(2π·r/cs)), cs derived from bounding-sphere
        estimate), which gives 10 sides for 4×2 domains and 8 for 4×4.

    Returns
    -------
    msh : dolfinx.mesh.Mesh
    cell_tags : dolfinx.mesh.MeshTags   (fluid domain tag = 10)

    Notes
    -----
    Vertex placement: phi_i = 2π·i/n, i = 0 … n-1 (i=0 at angle 0, CCW).

    Mesh sizing: one Distance+Threshold gmsh field per polygon transitions
    from ``edge_len = 2r·sin(π/n)`` right at the polygon boundary (prevents
    Steiner-point insertion on polygon edges) to ``lc`` at distance ``r/2``.
    No MeshSizeMax override; background field is the sole size control.
    """
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

    # Distance+Threshold field per polygon hole
    bg_fields = []
    for i, (cx, cy, r) in enumerate(circles):
        n = segs_per_circle[i]
        edge_len = 2 * r * math.sin(math.pi / n)

        # Identify polygon curves (not on the rectangle boundary)
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

        d_id = 10 + 2 * i
        t_id = 11 + 2 * i
        gmsh.model.mesh.field.add("Distance", d_id)
        gmsh.model.mesh.field.setNumbers(d_id, "CurvesList", c_curves)
        gmsh.model.mesh.field.add("Threshold", t_id)
        gmsh.model.mesh.field.setNumber(t_id, "InField", d_id)
        # SizeMin = edge_len at polygon: prevents subdivision of polygon edges.
        # SizeMax = lc at distance r/2: interior mesh size.
        gmsh.model.mesh.field.setNumber(t_id, "SizeMin", edge_len)
        gmsh.model.mesh.field.setNumber(t_id, "SizeMax", lc)
        gmsh.model.mesh.field.setNumber(t_id, "DistMin", 0.0)
        gmsh.model.mesh.field.setNumber(t_id, "DistMax", r / 2.0)
        bg_fields.append(t_id)

    if bg_fields:
        if len(bg_fields) == 1:
            gmsh.model.mesh.field.setAsBackgroundMesh(bg_fields[0])
        else:
            min_id = 10 + 2 * len(circles)
            gmsh.model.mesh.field.add("Min", min_id)
            gmsh.model.mesh.field.setNumbers(min_id, "FieldsList", bg_fields)
            gmsh.model.mesh.field.setAsBackgroundMesh(min_id)

    # Background field is the sole size control
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.Algorithm", 5)  # Delaunay

    surfaces = gmsh.model.getEntities(2)
    gmsh.model.addPhysicalGroup(2, [s[1] for s in surfaces], tag=10, name="domain")
    gmsh.model.mesh.generate(2)

    mesh_data = gmshio.model_to_mesh(gmsh.model, MPI.COMM_WORLD, rank=0, gdim=2)
    gmsh.finalize()
    return mesh_data.mesh, mesh_data.cell_tags
