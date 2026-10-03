#!/usr/bin/env python3
"""Generate verification/mms-stokes.ipynb."""
import pathlib, sys

REPO = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

import nbformat

def mc(src):
    return nbformat.v4.new_markdown_cell(src)

def cc(src, tags=None):
    c = nbformat.v4.new_code_cell(src)
    if tags:
        c["metadata"]["tags"] = tags
    return c

def can_src(name, ver):
    p = REPO / "canonical" / f"{name}.py"
    body = p.read_text()
    return f"# --- canonical: {name} v{ver} ---\n{body}# --- end canonical: {name} ---"


cells = []

cells.append(mc(
    "# MMS Stokes — Method of Manufactured Solutions\n\n"
    "**Stokes equations on the unit square**: −νΔu + ∇p = f, div u = 0, ν = 1.\n\n"
    "**Manufactured solution**:\n"
    "- Stream function ψ = sin²(πx)sin²(πy) + x²y → div u = 0 by construction\n"
    "- u_x = ∂ψ/∂y = π·sin²(πx)·sin(2πy) + x²\n"
    "- u_y = −∂ψ/∂x = −π·sin(2πx)·sin²(πy) − 2xy\n"
    "- p = cos(πx)sin(πy)  (mean = 0 over [0,1]²)\n\n"
    "**Scheme**: Taylor-Hood P2/P1, weak-penalty BC γ = C/h (course formulation), residual form + Newton,\n"
    "structured triangular meshes N×N, N = 8, 16, 32, 64, 128.\n\n"
    "**Reference rates**: ‖u‖_L2 → 3, ‖u‖_H1 → 2, ‖p‖_L2 → 2 (optimal for TH P2/P1).\n\n"
    "Errors measured against exact solution via UFL SpatialCoordinate expressions;\n"
    "f and g enter the forms directly as UFL (no nodal interpolation);\n"
    "quadrature degree = 2k+3 = 7 (k = 2 for P2 velocity)."
))

cells.append(cc(can_src("bootstrap", 1)))

cells.append(cc(
    "import os, math\n"
    "from mpi4py import MPI\n"
    "import ufl\n"
    "from petsc4py import PETSc\n"
    "from dolfinx.mesh import create_unit_square, CellType\n"
    "from dolfinx.fem import functionspace, Function, Constant, form, assemble_scalar\n"
    "from dolfinx.fem.petsc import NonlinearProblem\n"
    "import basix.ufl as bufl\n"
))

cells.append(cc(
    "# DD2365_FAST: run N=8,16 only for CI\n"
    "N_list = [8, 16] if os.environ.get('DD2365_FAST') == '1' else [8, 16, 32, 64, 128]\n"
    "C_penalty = 1e3\n",
    tags=["parameters"]
))

cells.append(mc(
    "## Manufactured solution\n\n"
    "Stream function ψ = sin²(πx)sin²(πy) + x²y\n\n"
    "Velocity (divergence-free by construction from ψ):\n"
    "  u_x = π sin²(πx) sin(2πy) + x²\n"
    "  u_y = −π sin(2πx) sin²(πy) − 2xy\n\n"
    "Pressure (mean zero over [0,1]²):\n"
    "  p = cos(πx) sin(πy)   — ∫p dx = 0 since ∫₀¹cos(πx)dx = 0\n\n"
    "Body force f = −Δu + ∇p (computed analytically from the above):\n"
    "  Δu_x = 2π³ sin(2πy)(2cos(2πx)−1) + 2\n"
    "  Δu_y = 2π³ sin(2πx)(4sin²(πy)−1)\n\n"
    "All of u_ex, p_ex, f enter the forms as UFL SpatialCoordinate expressions."
))

cells.append(mc(
    "## Convergence study\n\n"
    "Stokes residual form:\n\n"
    "    F((u,p);(v,q)) = ∫ν·∇u:∇v dx − ∫p·div(v) dx + ∫div(u)·q dx\n"
    "                   + γ∫(u−g)·v ds − ∫f·v dx = 0\n\n"
    "Solved with NonlinearProblem + Newton (1 step — linear).\n\n"
    "Error columns: ‖u‖_L2 = ‖u_h−u_ex‖_L2(Ω), ‖u‖_H1 = ‖∇(u_h−u_ex)‖_F,L2(Ω),\n"
    "‖p‖_L2 = ‖(p_h−mean_h) − (p_ex−mean_ex)‖_L2(Ω),\n"
    "e_bdy = ‖u_h−g‖_L2(∂Ω).  Quadrature degree 7 (= 2·2+3)."
))

cells.append(cc(
    "def run_stokes(N_list, C):\n"
    "    pi    = math.pi\n"
    "    qdeg  = 7  # 2*k+3, k=2 for P2 velocity\n"
    "    dx_ex = ufl.dx(metadata={'quadrature_degree': qdeg})\n"
    "    ds_ex = ufl.ds(metadata={'quadrature_degree': qdeg})\n"
    "    results = []\n"
    "    for N in N_list:\n"
    "        msh = create_unit_square(MPI.COMM_WORLD, N, N, cell_type=CellType.triangle)\n"
    "\n"
    "        P2v = bufl.element('Lagrange', msh.basix_cell(), 2, shape=(2,))\n"
    "        P1s = bufl.element('Lagrange', msh.basix_cell(), 1)\n"
    "        TH  = bufl.mixed_element([P2v, P1s])\n"
    "        W   = functionspace(msh, TH)\n"
    "        w   = Function(W)\n"
    "        u, p = ufl.split(w)\n"
    "        v, q = ufl.split(ufl.TestFunction(W))\n"
    "\n"
    "        nu    = Constant(msh, PETSc.ScalarType(1.0))\n"
    "        h_c   = ufl.CellDiameter(msh)\n"
    "        gamma = Constant(msh, PETSc.ScalarType(C)) / h_c\n"
    "\n"
    "        # Exact solution and data as UFL expressions\n"
    "        x = ufl.SpatialCoordinate(msh)\n"
    "        ux_ex = pi*ufl.sin(pi*x[0])**2 * ufl.sin(2*pi*x[1]) + x[0]**2\n"
    "        uy_ex = -pi*ufl.sin(2*pi*x[0]) * ufl.sin(pi*x[1])**2 - 2*x[0]*x[1]\n"
    "        u_ex_ufl = ufl.as_vector([ux_ex, uy_ex])\n"
    "        p_ex_ufl = ufl.cos(pi*x[0]) * ufl.sin(pi*x[1])\n"
    "        lap_ux = 2*pi**3 * ufl.sin(2*pi*x[1]) * (2*ufl.cos(2*pi*x[0]) - 1) + 2.0\n"
    "        lap_uy = 2*pi**3 * ufl.sin(2*pi*x[0]) * (4*ufl.sin(pi*x[1])**2 - 1)\n"
    "        dp_dx  = -pi * ufl.sin(pi*x[0]) * ufl.sin(pi*x[1])\n"
    "        dp_dy  =  pi * ufl.cos(pi*x[0]) * ufl.cos(pi*x[1])\n"
    "        f_ufl  = ufl.as_vector([-lap_ux + dp_dx, -lap_uy + dp_dy])\n"
    "\n"
    "        F = (\n"
    "            nu * ufl.inner(ufl.grad(u), ufl.grad(v)) * ufl.dx\n"
    "            - p * ufl.div(v) * ufl.dx\n"
    "            + ufl.div(u) * q * ufl.dx\n"
    "            + gamma * ufl.inner(u - u_ex_ufl, v) * ufl.ds\n"
    "            - ufl.inner(f_ufl, v) * ufl.dx\n"
    "        )\n"
    "\n"
    "        problem = NonlinearProblem(\n"
    "            F, w,\n"
    "            petsc_options_prefix='mms_stokes_',\n"
    "            petsc_options={\n"
    "                'snes_type': 'newtonls',\n"
    "                'snes_rtol': 1e-12,\n"
    "                'snes_atol': 1e-14,\n"
    "                'ksp_type': 'preonly',\n"
    "                'pc_type': 'lu',\n"
    "                'pc_factor_mat_solver_type': 'mumps',\n"
    "            },\n"
    "        )\n"
    "        problem.solve()\n"
    "        n_iters = problem.solver.getIterationNumber()\n"
    "\n"
    "        # Volume and pressure means (subtract discrete mean of p_h and exact mean of p_ex)\n"
    "        one  = Constant(msh, PETSc.ScalarType(1.0))\n"
    "        vol  = float(msh.comm.allreduce(\n"
    "            assemble_scalar(form(one * ufl.dx)), op=MPI.SUM))\n"
    "        p_mean_h  = float(msh.comm.allreduce(\n"
    "            assemble_scalar(form(p * dx_ex)), op=MPI.SUM)) / vol\n"
    "        p_ex_mean = float(msh.comm.allreduce(\n"
    "            assemble_scalar(form(p_ex_ufl * dx_ex)), op=MPI.SUM)) / vol\n"
    "\n"
    "        # Error UFL expressions (exact quadrature degree 7)\n"
    "        eu_ufl = u - u_ex_ufl\n"
    "        ep_ufl = (p - Constant(msh, PETSc.ScalarType(p_mean_h))) \\\n"
    "               - (p_ex_ufl - p_ex_mean)\n"
    "\n"
    "        e_L2_u = math.sqrt(abs(float(msh.comm.allreduce(\n"
    "            assemble_scalar(form(ufl.inner(eu_ufl, eu_ufl) * dx_ex)), op=MPI.SUM))))\n"
    "        e_H1_u = math.sqrt(abs(float(msh.comm.allreduce(\n"
    "            assemble_scalar(form(\n"
    "                ufl.inner(ufl.grad(eu_ufl), ufl.grad(eu_ufl)) * dx_ex)), op=MPI.SUM))))\n"
    "        e_L2_p = math.sqrt(abs(float(msh.comm.allreduce(\n"
    "            assemble_scalar(form(ep_ufl**2 * dx_ex)), op=MPI.SUM))))\n"
    "        e_bdy  = math.sqrt(abs(float(msh.comm.allreduce(\n"
    "            assemble_scalar(form(ufl.inner(eu_ufl, eu_ufl) * ds_ex)), op=MPI.SUM))))\n"
    "\n"
    "        h_val = 1.0 / N\n"
    "        results.append({'N': N, 'h': h_val,\n"
    "                         'e_L2_u': e_L2_u, 'e_H1_u': e_H1_u,\n"
    "                         'e_L2_p': e_L2_p, 'e_bdy': e_bdy,\n"
    "                         'iters': n_iters})\n"
    "        print(f'N={N:4d}  h={h_val:.4f}  ‖u‖_L2={e_L2_u:.4e}  '\n"
    "              f'‖u‖_H1={e_H1_u:.4e}  ‖p‖_L2={e_L2_p:.4e}  '\n"
    "              f'e_bdy={e_bdy:.4e}  iters={n_iters}')\n"
    "    return results\n"
))

cells.append(cc(
    "print(f'C = {C_penalty:.0e}')\n"
    "results_default = run_stokes(N_list, C_penalty)\n"
))

cells.append(mc("### Results table"))

cells.append(cc(
    "def print_stokes_table(results, label=''):\n"
    "    if label:\n"
    "        print(f'--- {label} ---')\n"
    "    hdr = ('N'.rjust(6) + '  ' + 'h'.rjust(7) + '  ' +\n"
    "           '‖u‖_L2'.rjust(12) + '  ' + 'r_L2u'.rjust(6) + '  ' +\n"
    "           '‖u‖_H1'.rjust(12) + '  ' + 'r_H1u'.rjust(6) + '  ' +\n"
    "           '‖p‖_L2'.rjust(12) + '  ' + 'r_L2p'.rjust(6) + '  ' +\n"
    "           'e_bdy'.rjust(12)  + '  ' + 'r_bdy'.rjust(6))\n"
    "    print(hdr)\n"
    "    for i, r in enumerate(results):\n"
    "        if i == 0:\n"
    "            rl2u = rh1u = rl2p = rb = '    —'\n"
    "        else:\n"
    "            prev = results[i-1]\n"
    "            rl2u = f'{math.log2(prev[\"e_L2_u\"]/r[\"e_L2_u\"]):6.2f}'\n"
    "            rh1u = f'{math.log2(prev[\"e_H1_u\"]/r[\"e_H1_u\"]):6.2f}'\n"
    "            rl2p = f'{math.log2(prev[\"e_L2_p\"]/r[\"e_L2_p\"]):6.2f}'\n"
    "            rb   = f'{math.log2(prev[\"e_bdy\" ]/r[\"e_bdy\" ]):6.2f}'\n"
    "        print(f\"{r['N']:>6}  {r['h']:>7.4f}  {r['e_L2_u']:>12.4e}  {rl2u}  \"\n"
    "              f\"{r['e_H1_u']:>12.4e}  {rh1u}  {r['e_L2_p']:>12.4e}  {rl2p}  \"\n"
    "              f\"{r['e_bdy']:>12.4e}  {rb}\")\n"
    "\n"
    "print_stokes_table(results_default, f'C = {C_penalty:.0e}')\n"
))

cells.append(mc("### Penalty sensitivity"))

cells.append(cc(
    "print('\\n=== C = 1e1 ===')\n"
    "results_c1 = run_stokes(N_list, 1e1)\n"
    "print('\\n=== C = 1e5 ===')\n"
    "results_c5 = run_stokes(N_list, 1e5)\n"
))

cells.append(cc(
    "print_stokes_table(results_c1, 'C = 1e1')\n"
    "print()\n"
    "print_stokes_table(results_c5, 'C = 1e5')\n"
))

for i, cell in enumerate(cells):
    cell["id"] = str(i)

nb = nbformat.v4.new_notebook(cells=cells)
nb["metadata"]["kernelspec"] = {
    "display_name": "Python 3",
    "language": "python",
    "name": "python3",
}
nb["metadata"]["language_info"] = {"name": "python", "version": "3.12.0"}

out = REPO / "verification" / "mms-stokes.ipynb"
out.parent.mkdir(exist_ok=True)
with open(out, "w") as f:
    nbformat.write(nb, f)
print(f"Written: {out}  ({len(cells)} cells)")
