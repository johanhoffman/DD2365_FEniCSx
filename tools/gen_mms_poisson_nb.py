#!/usr/bin/env python3
"""Generate verification/mms-poisson.ipynb."""
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
    "# MMS Poisson — Method of Manufactured Solutions\n\n"
    "**Poisson equation on the unit square**: −Δu = f, with weak Dirichlet BC.\n\n"
    "**Manufactured solution**: u = sin(πx)sin(πy) + xy (non-zero boundary data).\n\n"
    "**Scheme**: P1 Lagrange, residual form + Newton, structured triangular meshes N×N,\n"
    "N = 8, 16, 32, 64, 128.\n\n"
    "**Reference rates**: L2 → 2, H1 → 1 (optimal for P1).\n\n"
    "Two BC methods are compared:\n"
    "- **penalty**: γ(u−g, v)_∂Ω, γ = C/h — non-symmetric, consistency error O(h/C)\n"
    "- **nitsche**: symmetric Nitsche — (∇u·n, v) + (∇v·n, u−g) + γ(u−g, v) — optimal for all C above threshold\n\n"
    "Errors measured against exact solution via UFL SpatialCoordinate expressions;\n"
    "f and g enter the forms directly as UFL (no nodal interpolation);\n"
    "quadrature degree = 2k+3 = 5 (k = 1 for P1)."
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
    "C_penalty = 1e3\n"
    "C_nitsche_list = [10, 100, 1000]\n",
    tags=["parameters"]
))

cells.append(mc(
    "## Manufactured solution\n\n"
    "u_ex = sin(πx)sin(πy) + xy  →  f = −Δu_ex = 2π²sin(πx)sin(πy)\n\n"
    "Boundary data g = u_ex|∂Ω.\n\n"
    "Both f and g enter the weak form as UFL SpatialCoordinate expressions — no nodal interpolation."
))

cells.append(mc(
    "## Convergence study\n\n"
    "**Penalty form** (non-symmetric):\n\n"
    "    F(u; v) = ∫∇u·∇v dx + γ∫(u − g)v ds − ∫f·v dx = 0,   γ = C/h\n\n"
    "**Symmetric Nitsche form**:\n\n"
    "    F(u; v) = ∫∇u·∇v dx\n"
    "            − ⟨∇u·n, v⟩_∂Ω          (consistency)\n"
    "            − ⟨∇v·n, u−g⟩_∂Ω        (symmetry)\n"
    "            + γ⟨u−g, v⟩_∂Ω          (penalty)\n"
    "            − ∫f·v dx = 0,   γ = C/h\n\n"
    "Coercivity of Nitsche requires C > C_inv ≈ 5 for P1 on regular triangles.\n"
    "Solved with NonlinearProblem + Newton (1 step — linear).\n\n"
    "Error columns: e_L2 = ‖u_h−u_ex‖_L2(Ω), e_H1 = ‖∇(u_h−u_ex)‖_L2(Ω),\n"
    "e_bdy = ‖u_h−g‖_L2(∂Ω).  Quadrature degree 5 (= 2·1+3)."
))

cells.append(cc(
    "def run_poisson(N_list, C, method='penalty'):\n"
    "    \"\"\"method: 'penalty' or 'nitsche'\"\"\"\n"
    "    pi    = math.pi\n"
    "    qdeg  = 5  # 2*k+3, k=1 for P1\n"
    "    dx_ex = ufl.dx(metadata={'quadrature_degree': qdeg})\n"
    "    ds_ex = ufl.ds(metadata={'quadrature_degree': qdeg})\n"
    "    results = []\n"
    "    for N in N_list:\n"
    "        msh = create_unit_square(MPI.COMM_WORLD, N, N, cell_type=CellType.triangle)\n"
    "        V   = functionspace(msh, bufl.element('Lagrange', msh.basix_cell(), 1))\n"
    "        u   = Function(V)\n"
    "        v   = ufl.TestFunction(V)\n"
    "\n"
    "        h_c   = ufl.CellDiameter(msh)\n"
    "        gamma = Constant(msh, PETSc.ScalarType(C)) / h_c\n"
    "\n"
    "        x     = ufl.SpatialCoordinate(msh)\n"
    "        u_ex  = ufl.sin(pi*x[0])*ufl.sin(pi*x[1]) + x[0]*x[1]\n"
    "        f_ufl = 2.0*pi**2 * ufl.sin(pi*x[0])*ufl.sin(pi*x[1])\n"
    "\n"
    "        if method == 'nitsche':\n"
    "            n = ufl.FacetNormal(msh)\n"
    "            F = (\n"
    "                ufl.inner(ufl.grad(u), ufl.grad(v)) * ufl.dx\n"
    "                - ufl.inner(ufl.grad(u), n) * v * ufl.ds\n"
    "                - ufl.inner(ufl.grad(v), n) * (u - u_ex) * ufl.ds\n"
    "                + gamma * (u - u_ex) * v * ufl.ds\n"
    "                - f_ufl * v * ufl.dx\n"
    "            )\n"
    "        else:\n"
    "            F = (\n"
    "                ufl.inner(ufl.grad(u), ufl.grad(v)) * ufl.dx\n"
    "                + gamma * (u - u_ex) * v * ufl.ds\n"
    "                - f_ufl * v * ufl.dx\n"
    "            )\n"
    "\n"
    "        problem = NonlinearProblem(\n"
    "            F, u,\n"
    "            petsc_options_prefix='mms_poisson_',\n"
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
    "        e     = u - u_ex\n"
    "        e_L2  = math.sqrt(abs(float(msh.comm.allreduce(\n"
    "            assemble_scalar(form(e**2 * dx_ex)), op=MPI.SUM))))\n"
    "        e_H1  = math.sqrt(abs(float(msh.comm.allreduce(\n"
    "            assemble_scalar(form(ufl.inner(ufl.grad(e), ufl.grad(e)) * dx_ex)), op=MPI.SUM))))\n"
    "        e_bdy = math.sqrt(abs(float(msh.comm.allreduce(\n"
    "            assemble_scalar(form(e**2 * ds_ex)), op=MPI.SUM))))\n"
    "\n"
    "        h_val = 1.0 / N\n"
    "        results.append({'N': N, 'h': h_val,\n"
    "                         'e_L2': e_L2, 'e_H1': e_H1, 'e_bdy': e_bdy,\n"
    "                         'iters': n_iters})\n"
    "        print(f'N={N:4d}  h={h_val:.4f}  e_L2={e_L2:.4e}  e_H1={e_H1:.4e}  '\n"
    "              f'e_bdy={e_bdy:.4e}  iters={n_iters}')\n"
    "    return results\n"
))

cells.append(cc(
    "print(f'C = {C_penalty:.0e}')\n"
    "results_default = run_poisson(N_list, C_penalty)\n"
))

cells.append(mc("### Results table"))

cells.append(cc(
    "def print_table(results, label=''):\n"
    "    if label:\n"
    "        print(f'--- {label} ---')\n"
    "    hdr = ('N'.rjust(6) + '  ' + 'h'.rjust(8) + '  ' +\n"
    "           'e_L2'.rjust(12) + '  ' + 'r_L2'.rjust(6) + '  ' +\n"
    "           'e_H1'.rjust(12) + '  ' + 'r_H1'.rjust(6) + '  ' +\n"
    "           'e_bdy'.rjust(12) + '  ' + 'r_bdy'.rjust(6))\n"
    "    print(hdr)\n"
    "    for i, r in enumerate(results):\n"
    "        if i == 0:\n"
    "            rl2 = rh1 = rb = '    —'\n"
    "        else:\n"
    "            prev = results[i-1]\n"
    "            rl2 = f'{math.log2(prev[\"e_L2\" ]/r[\"e_L2\" ]):6.2f}' if r['e_L2' ] > 0 else '  NaN'\n"
    "            rh1 = f'{math.log2(prev[\"e_H1\" ]/r[\"e_H1\" ]):6.2f}' if r['e_H1' ] > 0 else '  NaN'\n"
    "            rb  = f'{math.log2(prev[\"e_bdy\"]/r[\"e_bdy\"]):6.2f}' if r['e_bdy'] > 0 else '  NaN'\n"
    "        print(f\"{r['N']:>6}  {r['h']:>8.4f}  {r['e_L2']:>12.4e}  {rl2}  \"\n"
    "              f\"{r['e_H1']:>12.4e}  {rh1}  {r['e_bdy']:>12.4e}  {rb}\")\n"
    "\n"
    "print_table(results_default, f'C = {C_penalty:.0e}')\n"
))

cells.append(mc("### Penalty sensitivity"))

cells.append(cc(
    "print('\\n=== C = 1e1 ===')\n"
    "results_c1 = run_poisson(N_list, 1e1)\n"
    "print('\\n=== C = 1e5 ===')\n"
    "results_c5 = run_poisson(N_list, 1e5)\n"
))

cells.append(cc(
    "print_table(results_c1, 'C = 1e1')\n"
    "print()\n"
    "print_table(results_c5, 'C = 1e5')\n"
))

cells.append(mc(
    "## Nitsche method\n\n"
    "Symmetric Nitsche BC: three terms — consistency, symmetry, penalty.\n"
    "Coercivity threshold: C_inv ≈ 5 for P1 on regular triangles.\n"
    "Expected: optimal rates (L2→2, H1→1) for all C > C_inv, including C=10.\n"
    "e_bdy should decrease at rate ≥ 1 (H1 boundary norm); much smaller than penalty at same C."
))

cells.append(cc(
    "nitsche_results = {}\n"
    "for C_n in C_nitsche_list:\n"
    "    print(f'\\n=== Nitsche C = {C_n} ===')\n"
    "    nitsche_results[C_n] = run_poisson(N_list, C_n, method='nitsche')\n"
))

cells.append(cc(
    "for C_n in C_nitsche_list:\n"
    "    print()\n"
    "    print_table(nitsche_results[C_n], f'Nitsche C = {C_n}')\n"
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

out = REPO / "verification" / "mms-poisson.ipynb"
out.parent.mkdir(exist_ok=True)
with open(out, "w") as f:
    nbformat.write(nb, f)
print(f"Written: {out}  ({len(cells)} cells)")
