#!/usr/bin/env python3
"""KSP convergence diagnostic for Turbulence-Model in FAST mode (T=0.2).

Prints one DIAG line per solve:
    DIAG step=<n> k=<k> ksp=<name> reason=<r> iters=<i> rnorm=<rn>

Used to compare solver convergence across platforms (osx-arm64 vs Linux CI).
"""
import sys, pathlib, os
import nbformat
from nbclient import NotebookClient

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("OMP_NUM_THREADS", "1")

repo = pathlib.Path(__file__).parent.parent
nb_path = repo / "Turbulence-Model.ipynb"

nb = nbformat.read(nb_path, as_version=4)

# inject FAST override after parameters cell
fast_src = "T = 0.2\nplot_freq = 2\n"
for i, cell in enumerate(nb.cells):
    if "parameters" in cell.get("metadata", {}).get("tags", []):
        nb.cells.insert(i + 1, nbformat.v4.new_code_cell(source=fast_src))
        break

# patch time loop cell: add logging after each ksp.solve()
for i, cell in enumerate(nb.cells):
    if cell["cell_type"] == "code" and "while t < T" in cell["source"] and "ksp_u.solve" in cell["source"]:
        src = cell["source"]
        src = src.replace(
            "ksp_u.setOperators(A_u, A_u); ksp_u.solve(b_u, u1.x.petsc_vec)",
            "ksp_u.setOperators(A_u, A_u); ksp_u.solve(b_u, u1.x.petsc_vec)\n"
            "        _r_u=ksp_u.getConvergedReason(); _i_u=ksp_u.getIterationNumber(); _n_u=ksp_u.getResidualNorm()\n"
            "        print(f'DIAG step={step} k={k} ksp=ksp_u reason={_r_u} iters={_i_u} rnorm={_n_u:.4e}',flush=True)"
        )
        src = src.replace(
            "ksp_p.setOperators(A_p, A_p); ksp_p.solve(b_p, p1.x.petsc_vec)",
            "ksp_p.setOperators(A_p, A_p); ksp_p.solve(b_p, p1.x.petsc_vec)\n"
            "        _r_p=ksp_p.getConvergedReason(); _i_p=ksp_p.getIterationNumber(); _n_p=ksp_p.getResidualNorm()\n"
            "        print(f'DIAG step={step} k={k} ksp=ksp_p reason={_r_p} iters={_i_p} rnorm={_n_p:.4e}',flush=True)"
        )
        cell["source"] = src
        break

client = NotebookClient(nb, timeout=600, kernel_name="python3", allow_errors=False)
client.execute()

# collect and print DIAG/QOI lines from cell outputs
print("\n=== KSP diagnostic (Turbulence-Model FAST T=0.2) ===")
print(f"{'step':>5}  {'k':>2}  {'ksp':>7}  {'reason':>7}  {'iters':>6}  {'rnorm':>12}")
print("-" * 55)
for cell in nb.cells:
    for out in cell.get("outputs", []):
        if out.get("output_type") == "stream":
            for line in "".join(out.get("text", [])).splitlines():
                if line.startswith("DIAG "):
                    parts = {}
                    for token in line[5:].split():
                        key, val = token.split("=", 1)
                        parts[key] = val
                    print(f"{parts.get('step','?'):>5}  {parts.get('k','?'):>2}  {parts.get('ksp','?'):>7}  "
                          f"{parts.get('reason','?'):>7}  {parts.get('iters','?'):>6}  {parts.get('rnorm','?'):>12}")
                elif line.startswith("QOI "):
                    print(f"\n{line}")
