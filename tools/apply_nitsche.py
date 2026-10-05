#!/usr/bin/env python3
"""Patch Poisson_equation.ipynb and template-report-Stokes.ipynb
to use symmetric Nitsche BCs instead of pure penalty."""
import json
import pathlib

REPO = pathlib.Path(__file__).parent.parent

def to_src(s):
    """Convert a plain string to a notebook source list (lines with \\n except last)."""
    lines = s.split('\n')
    result = []
    for i, line in enumerate(lines):
        if i < len(lines) - 1:
            result.append(line + '\n')
        else:
            if line:          # non-empty last line
                result.append(line)
            # empty last line: drop (trailing newline already on previous entry)
    return result


# ---------------------------------------------------------------------------
# Poisson notebook patches
# ---------------------------------------------------------------------------

POISSON_CELL_15 = """\
\\
The Poisson equation takes the form

$-\\Delta u = f,$

together with suitable boundary conditions.

Here we present a FEniCSx implementation of a finite element method to solve the Poisson
equation in 2D. The solution is visualized using matplotlib, and is also exported as
XDMF files which can be visualized in ParaView.

To derive the weak form of the equations, multiply the equation by $v\\in V$, integrate
over the domain $\\Omega$ and use Green's formula
$$(-\\Delta u,v) = (\\nabla u, \\nabla v) - \\langle\\nabla u\\cdot n, v\\rangle_{\\partial \\Omega}$$

We divide the boundary into $\\partial \\Omega=\\Gamma_D \\cup \\Gamma_N$, with boundary conditions

$$u = g_D,\\quad x\\in \\Gamma_D,$$
$$-\\nabla u\\cdot n = g_N, \\quad x\\in \\Gamma_N.$$

Dirichlet conditions are imposed by the **symmetric Nitsche method**.  Starting from
the natural boundary term, three contributions are added on $\\Gamma_D$:

$$r_{\\Gamma_D}(u;v) =
  \\underbrace{-\\langle\\nabla u\\cdot n,\\, v\\rangle_{\\Gamma_D}}_{\\text{consistency}}
  \\underbrace{-\\langle\\nabla v\\cdot n,\\, u-g_D\\rangle_{\\Gamma_D}}_{\\text{symmetry}}
  +\\underbrace{\\langle\\gamma(u-g_D),\\, v\\rangle_{\\Gamma_D}}_{\\text{penalty}},\\quad \\gamma=C/h.$$

The **consistency** term recovers the integration-by-parts identity; the **symmetry** term
makes the bilinear form self-adjoint (adjoint-consistent); the **penalty** term enforces
coercivity for $C$ above the inverse-estimate constant
($C_{\\mathrm{inv}}\\approx 5$ for P1 on regular triangles).
We use $C=10$; see `verification/mms-poisson.ipynb` for convergence tables.

With $g_N=0$ on $\\Gamma_N$ the Neumann boundary term vanishes and the full residual form is

$$r(u;v) = (\\nabla u,\\nabla v) + r_{\\Gamma_D}(u;v) - (f,v) = 0.\\,$$\\

$$(v,w) = \\int_{\\Omega} v\\cdot w ~dx, \\quad \\langle v,w\\rangle_{\\Gamma} = \\int_{\\Gamma} v\\cdot w~ds$$"""

POISSON_CELL_21 = """\
**Define boundary conditions**

Boundary identification uses `tag_boundaries(msh, L, H)` which geometrically
assigns facet tags on the current mesh: left=1, right=2, lower=3, upper=4,
circle boundaries=5.  Tags are recomputed after refinement so they remain valid.
This replaces the indicator `Expression`s from the legacy FEniCS version — `ds(tag)` takes
the role of `ib*ds`, `wb*ds`, and `ob*ds`.

All Dirichlet conditions are imposed by the symmetric Nitsche method with $\\gamma = C/h$,
$C = 10$.  This value exceeds the inverse-estimate constant $C_{\\mathrm{inv}}\\approx 5$
for P1 Lagrange elements on regular triangles, ensuring coercivity while keeping
the condition number moderate."""

POISSON_CELL_25 = """\
dx = ufl.Measure("dx", domain=msh)
ds = ufl.Measure("ds", domain=msh, subdomain_data=facet_tags)
h  = ufl.CellDiameter(msh)
n  = ufl.FacetNormal(msh)
x  = ufl.SpatialCoordinate(msh)

C     = 10.0   # symmetric Nitsche: C > C_inv ≈ 5 for P1
gamma = C / h

f = 10.0 * ufl.sin(x[0])

def _N(u, v, g, ds_):
    # Symmetric Nitsche: consistency + symmetry + penalty for u = g on ds_
    return (
        - ufl.inner(ufl.grad(u), n) * v * ds_
        - ufl.inner(ufl.grad(v), n) * (u - g) * ds_
        + gamma * (u - g) * v * ds_
    )

# Residual form with symmetric Nitsche BCs (authorized deviation, Johan 2026-10-03)
residual = (
    ufl.inner(ufl.grad(u), ufl.grad(v)) * dx
    + _N(u, v, uin,  ds(1))   # inflow (left)
    + _N(u, v, uout, ds(2))   # outflow (right)
    + _N(u, v, uw,   ds(3))   # wall (lower)
    + _N(u, v, uw,   ds(4))   # wall (upper)
    + _N(u, v, uw,   ds(5))   # wall (objects)
    - ufl.inner(f, v) * dx
)

problem = NonlinearProblem(
    residual, u,
    petsc_options_prefix="poisson_",
    petsc_options={
        "snes_type": "newtonls",
        "snes_rtol": 1.0e-8,
        "snes_atol": 1.0e-10,
        "ksp_type": "preonly",
        "pc_type": "lu",
        "pc_factor_mat_solver_type": "mumps",
    },
)
u = problem.solve()
assert problem.solver.getConvergedReason() > 0, (
    f"Newton did not converge: reason={problem.solver.getConvergedReason()}"
)
print(f"Newton converged in {problem.solver.getIterationNumber()} iteration(s).")"""


# ---------------------------------------------------------------------------
# Stokes notebook patches
# ---------------------------------------------------------------------------

STOKES_CELL_15 = """\
\\
The Stokes equations take the form

$\\nabla p -\\Delta u = f,\\quad \\nabla \\cdot u=0$

together with suitable boundary conditions.

Here we present a FEniCSx implementation of a mixed finite element method to solve the Stokes equations in 2D. The solution is visualized using matplotlib, and is also exported as XDMF files which can be visualized in ParaView.

To derive the weak form of the Stokes equations, consider the residual form
$r((u,p);(v,q)) = 0$ for all $(v, q) \\in V \\times Q$:

$$r_\\Omega((u,p);(v,q)) = \\int_\\Omega \\nabla u : \\nabla v \\, dx
  - \\int_\\Omega p \\, \\nabla \\cdot v \\, dx
  + \\int_\\Omega \\nabla \\cdot u \\, q \\, dx
  - \\int_\\Omega f \\cdot v \\, dx$$

Dirichlet conditions are imposed by the **symmetric Nitsche method**.
The viscous traction and its formal adjoint on $\\Gamma_D$ are
$\\sigma(u,p)\\cdot n = \\nabla u\\cdot n - pn$ and $\\sigma(v,q)\\cdot n = \\nabla v\\cdot n - qn$
(with $\\nu=1$).  Three boundary contributions are added on $\\Gamma_D$:

$$r_{\\Gamma_D}((u,p);(v,q)) =
  \\underbrace{-\\langle\\sigma(u,p)\\cdot n,\\, v\\rangle_{\\Gamma_D}}_{\\text{consistency}}
  \\underbrace{-\\langle\\sigma(v,q)\\cdot n,\\, u-g\\rangle_{\\Gamma_D}}_{\\text{symmetry}}
  +\\underbrace{\\langle\\gamma(u-g),\\, v\\rangle_{\\Gamma_D}}_{\\text{penalty}},\\quad \\gamma=C/h.$$

The $-qn$ part of $\\sigma(v,q)\\cdot n$ is the adjoint of the $-\\int p\\,\\nabla\\cdot v\\,dx$
term (via the divergence theorem), making the saddle-point form self-adjoint.
Coercivity requires $C > C_{\\mathrm{inv}}\\approx 15$ for P2 on regular triangles; we use $C=20$.
See `verification/mms-stokes.ipynb` for convergence tables.

The full residual form is $r = r_\\Omega + r_{\\Gamma_D} = 0$.  Inflow (left, tag 1)
prescribes $u_{\\mathrm{in}} = (4y(H-y)/H^2, 0)$; walls and obstacles (tags 3, 4, 5)
prescribe $u = 0$; the outflow (right, tag 2) uses a do-nothing condition (no boundary term)."""

STOKES_CELL_21 = """\
**Define boundary conditions**

Boundary identification uses `tag_boundaries(msh, L, H)` which geometrically
assigns facet tags on the current mesh: left=1, right=2, lower=3, upper=4,
circle boundaries=5.  All Dirichlet conditions are imposed by the symmetric Nitsche
method with $\\gamma = C/h$, $C = 20$.  This value exceeds the inverse-estimate constant
$C_{\\mathrm{inv}}\\approx 15$ for P2 Lagrange elements on regular triangles, ensuring coercivity."""

STOKES_CELL_25 = """\
dx = ufl.Measure("dx", domain=msh)
ds = ufl.Measure("ds", domain=msh, subdomain_data=facet_tags)
h  = ufl.CellDiameter(msh)
n  = ufl.FacetNormal(msh)

C     = 20.0   # symmetric Nitsche: C > C_inv ≈ 15 for P2
gamma = C / h

def _N(u, p, v, q, g, ds_):
    # Symmetric Nitsche for Stokes: consistency + symmetry + penalty for u = g on ds_
    t_u = ufl.dot(ufl.grad(u), n) - p * n   # traction  σ(u,p)·n  (ν=1)
    t_v = ufl.dot(ufl.grad(v), n) - q * n   # adj. traction σ(v,q)·n
    return (
        - ufl.inner(t_u, v) * ds_
        - ufl.inner(t_v, u - g) * ds_
        + gamma * ufl.inner(u - g, v) * ds_
    )

g0 = ufl.as_vector([0.0, 0.0])   # zero Dirichlet datum

# Residual form r((u,p); (v,q)) = 0 with symmetric Nitsche BCs (authorized deviation, Johan 2026-10-03)
residual = (
    - p * ufl.div(v) * dx
    + ufl.inner(ufl.grad(u), ufl.grad(v)) * dx
    + ufl.div(u) * q * dx
    + _N(u, p, v, q, uin, ds(1))   # inflow: u = uin
    + _N(u, p, v, q, g0,  ds(3))   # bottom wall: u = 0
    + _N(u, p, v, q, g0,  ds(4))   # top wall: u = 0
    + _N(u, p, v, q, g0,  ds(5))   # objects: u = 0
    # tag 2 (outflow): do-nothing, no boundary term
)

problem = NonlinearProblem(
    residual, w,
    petsc_options_prefix="stokes_",
    petsc_options={
        "snes_type": "newtonls", "snes_rtol": 1e-8, "snes_atol": 1e-10,
        "ksp_type": "preonly", "pc_type": "lu",
        "pc_factor_mat_solver_type": "mumps",
    },
)
w = problem.solve()
assert problem.solver.getConvergedReason() > 0, "Newton did not converge" """


def patch_notebook(nb_path, updates):
    with open(nb_path) as f:
        nb = json.load(f)
    for idx, new_src in updates.items():
        nb['cells'][idx]['source'] = to_src(new_src)
    with open(nb_path, 'w') as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write('\n')
    print(f"Patched {nb_path.name}  (cells {sorted(updates)})")


patch_notebook(
    REPO / "Poisson_equation.ipynb",
    {15: POISSON_CELL_15, 21: POISSON_CELL_21, 25: POISSON_CELL_25},
)

patch_notebook(
    REPO / "template-report-Stokes.ipynb",
    {15: STOKES_CELL_15, 21: STOKES_CELL_21, 25: STOKES_CELL_25},
)
