#!/usr/bin/env python3
"""Generate verification/mms-poisson.ipynb."""
import json, pathlib, sys

REPO = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

import nbformat

# ── helpers ──────────────────────────────────────────────────────────────────

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


# ── cells ─────────────────────────────────────────────────────────────────────

cells = []

cells.append(mc(
    "# MMS Poisson — Method of Manufactured Solutions\n\n"
    "**Poisson equation on the unit square**: −Δu = f, with weak penalty BC.\n\n"
    "**Manufactured solution**: u = sin(πx)sin(πy) + xy (non-zero boundary data).\n\n"
    "**Scheme**: P1 Lagrange, weak-penalty BC γ = C/h, residual form + Newton,\n"
    "structured triangular meshes N×N, N = 8, 16, 32, 64, 128.\n\n"
    "**Reference rates**: L2 → 2, H1 → 1 (optimal for P1)."
))

cells.append(cc(can_src("bootstrap", 1)))

cells.append(cc(
    "import os, math\n"
    "import numpy as np\n"
    "from mpi4py import MPI\n"
    "import ufl\n"
    "from petsc4py import PETSc\n"
    "from dolfinx.mesh import create_unit_square, CellType\n"
    "from dolfinx.fem import (\n"
    "    functionspace, Function, Constant, form, assemble_scalar,\n"
    ")\n"
    "from dolfinx.fem.petsc import NonlinearProblem\n"
    "import basix.ufl as bufl\n"
))

cells.append(cc(
    "# DD2365_FAST: run N=8,16 only for CI\n"
    "import os\n"
    "N_list = [8, 16] if os.environ.get('DD2365_FAST') == '1' else [8, 16, 32, 64, 128]\n"
    "C_penalty = 1e3\n",
    tags=["parameters"]
))

cells.append(mc("## Manufactured solution\n\n"
    "u_ex = sin(πx)sin(πy) + xy  →  f = −Δu_ex = 2π²sin(πx)sin(πy)\n\n"
    "Boundary data g = u_ex|∂Ω: zero at x=0 and y=0, y at x=1, x at y=1."))

cells.append(cc(
    "def u_ex_fn(x):\n"
    "    return np.sin(np.pi * x[0]) * np.sin(np.pi * x[1]) + x[0] * x[1]\n"
    "\n"
    "def f_fn(x):\n"
    "    return 2.0 * np.pi**2 * np.sin(np.pi * x[0]) * np.sin(np.pi * x[1])\n"
    "\n"
    "# Boundary function g = u_ex (same lambda reused)\n"
    "g_fn = u_ex_fn\n"
))

cells.append(mc("## Convergence study  (C = {C_penalty})\n\n"
    "Poisson residual form:\n\n"
    "    F(u; v) = ∫∇u·∇v dx + γ∫(u − g)v ds − ∫f·v dx = 0,   γ = C/h\n\n"
    "Solved with NonlinearProblem + NewtonSolver (converges in 1 step — linear problem)."))

cells.append(cc(
    "def run_poisson(N_list, C):\n"
    "    \"\"\"Run Poisson MMS convergence study and return list of result dicts.\"\"\"\n"
    "    results = []\n"
    "    for N in N_list:\n"
    "        msh = create_unit_square(MPI.COMM_WORLD, N, N, cell_type=CellType.triangle)\n"
    "        P1  = bufl.element('Lagrange', msh.basix_cell(), 1)\n"
    "        V   = functionspace(msh, P1)\n"
    "\n"
    "        u   = Function(V)\n"
    "        v   = ufl.TestFunction(V)\n"
    "\n"
    "        h_c   = ufl.CellDiameter(msh)\n"
    "        gamma = Constant(msh, PETSc.ScalarType(C)) / h_c\n"
    "\n"
    "        # Interpolate g and f into P1 functions\n"
    "        g_h = Function(V)\n"
    "        g_h.interpolate(g_fn)\n"
    "        f_h = Function(V)\n"
    "        f_h.interpolate(f_fn)\n"
    "\n"
    "        # Residual: ∫∇u·∇v dx + γ(u−g)v ds − fv dx\n"
    "        F = (\n"
    "            ufl.inner(ufl.grad(u), ufl.grad(v)) * ufl.dx\n"
    "            + gamma * ufl.inner(u - g_h, v) * ufl.ds\n"
    "            - ufl.inner(f_h, v) * ufl.dx\n"
    "        )\n"
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
    "        # Error functions\n"
    "        u_ex_fn_h = Function(V)\n"
    "        u_ex_fn_h.interpolate(u_ex_fn)\n"
    "        err = Function(V)\n"
    "        err.x.array[:] = u.x.array - u_ex_fn_h.x.array\n"
    "\n"
    "        e_L2 = math.sqrt(float(msh.comm.allreduce(\n"
    "            assemble_scalar(form(err**2 * ufl.dx)), op=MPI.SUM)))\n"
    "        e_H1 = math.sqrt(float(msh.comm.allreduce(\n"
    "            assemble_scalar(form(ufl.inner(ufl.grad(err), ufl.grad(err)) * ufl.dx)),\n"
    "            op=MPI.SUM)))\n"
    "\n"
    "        h_val = 1.0 / N\n"
    "        results.append({'N': N, 'h': h_val, 'e_L2': e_L2, 'e_H1': e_H1,\n"
    "                         'iters': n_iters})\n"
    "        print(f'N={N:4d}  h={h_val:.4f}  e_L2={e_L2:.4e}  e_H1={e_H1:.4e}  iters={n_iters}')\n"
    "    return results\n"
))

cells.append(cc(
    "print(f'C = {C_penalty:.0e}')\n"
    "results_default = run_poisson(N_list, C_penalty)\n"
))

cells.append(mc("### Results table (C = {C_penalty})"))

cells.append(cc(
    "def print_table(results, label=''):\n"
    "    if label:\n"
    "        print(f'--- {label} ---')\n"
    "    print(f\"{'N':>6}  {'h':>8}  {'e_L2':>12}  {'rate_L2':>8}  {'e_H1':>12}  {'rate_H1':>8}\")\n"
    "    for i, r in enumerate(results):\n"
    "        if i == 0:\n"
    "            r2 = r1 = '   —'\n"
    "        else:\n"
    "            prev = results[i-1]\n"
    "            r2 = f'{math.log2(prev[\"e_L2\"]/r[\"e_L2\"]):8.2f}' if r['e_L2'] > 0 else '  NaN'\n"
    "            r1 = f'{math.log2(prev[\"e_H1\"]/r[\"e_H1\"]):8.2f}' if r['e_H1'] > 0 else '  NaN'\n"
    "        print(f\"{r['N']:>6}  {r['h']:>8.4f}  {r['e_L2']:>12.4e}  {r2}  {r['e_H1']:>12.4e}  {r1}\")\n"
    "\n"
    "print_table(results_default, f'C = {C_penalty:.0e}')\n"
))

cells.append(mc(
    "### Penalty sensitivity\n\n"
    "Re-run at N = {N_list} with C = 1e1 (under-penalized) and C = 1e5 (over-penalized)."
))

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

# ── assemble and write ────────────────────────────────────────────────────────

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
