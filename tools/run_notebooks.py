#!/usr/bin/env python3
"""run_notebooks.py

Execute all notebooks at the repo root headlessly with nbclient.
Reports pass/fail and wall-clock time for each notebook.

Usage:
    python tools/run_notebooks.py            # run all *.ipynb at repo root
    python tools/run_notebooks.py Poisson*   # run matching notebooks

DD2365_FAST mode:
    Set DD2365_FAST=1 to inject a small-T override after each notebook's
    "parameters" cell (T=0.2, plot_freq=2).  Used by CI.

Exit 0 if all pass; nonzero if any fail.

Requires: nbclient, nbformat  (both in the fenicsx-0.11 conda env)
"""
import sys, os, time, pathlib, argparse
import nbformat
from nbclient import NotebookClient

os.environ.setdefault("MPLBACKEND", "Agg")

FAST_MODE = os.environ.get("DD2365_FAST", "0") == "1"
FAST_OVERRIDE_SOURCE = "T = 0.2\nplot_freq = 2\n"

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "patterns", nargs="*",
    help="Glob patterns relative to repo root (default: *.ipynb)",
)
parser.add_argument("--timeout", type=int, default=600, help="Per-notebook timeout (s)")
args = parser.parse_args()

repo_root = pathlib.Path(__file__).parent.parent
if args.patterns:
    notebooks = []
    for pat in args.patterns:
        notebooks.extend(sorted(repo_root.glob(pat)))
else:
    notebooks = sorted(repo_root.glob("*.ipynb"))

if not notebooks:
    print("No notebooks found.")
    sys.exit(0)


def inject_fast_override(nb):
    """Insert a fast-mode override cell after the 'parameters'-tagged cell.

    Finds the last cell whose metadata tags include 'parameters' and inserts
    a new code cell immediately after it.  If no tagged cell is found the
    notebook is returned unmodified.
    """
    param_idx = None
    for i, cell in enumerate(nb.cells):
        if "parameters" in cell.get("metadata", {}).get("tags", []):
            param_idx = i
    if param_idx is None:
        return nb
    override_cell = nbformat.v4.new_code_cell(source=FAST_OVERRIDE_SOURCE)
    nb.cells.insert(param_idx + 1, override_cell)
    return nb


results = []
for nb_path in notebooks:
    with open(nb_path) as f:
        nb = nbformat.read(f, as_version=4)
    if FAST_MODE:
        nb = inject_fast_override(nb)
    t0 = time.time()
    try:
        client = NotebookClient(nb, timeout=args.timeout, kernel_name="python3",
                                allow_errors=False)
        client.execute()
        elapsed = time.time() - t0
        results.append((nb_path.name, "PASS", elapsed, None))
    except Exception as exc:
        elapsed = time.time() - t0
        results.append((nb_path.name, "FAIL", elapsed, str(exc)))

print(f"\n{'Notebook':<44} {'Status':<6} {'Time':>8}")
print("-" * 62)
n_pass = 0
for name, status, elapsed, err in results:
    print(f"{name:<44} {status:<6} {elapsed:>7.1f}s")
    if status == "PASS":
        n_pass += 1
    elif err:
        first_line = err.splitlines()[0] if err else ""
        print(f"  Error: {first_line[:100]}")

if FAST_MODE:
    print("  [DD2365_FAST=1: T=0.2, plot_freq=2 injected]")
print(f"\n{n_pass}/{len(results)} notebook(s) passed.")
if n_pass < len(results):
    sys.exit(1)
