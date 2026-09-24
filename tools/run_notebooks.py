#!/usr/bin/env python3
"""run_notebooks.py

Execute all notebooks at the repo root headlessly with nbclient.
Reports pass/fail and wall-clock time for each notebook.

Usage:
    python tools/run_notebooks.py            # run all *.ipynb at repo root
    python tools/run_notebooks.py Poisson*   # run matching notebooks

Exit 0 if all pass; nonzero if any fail.

Requires: nbclient, nbformat  (both in the fenicsx-0.11 conda env)
"""
import sys, time, pathlib, argparse
import nbformat
from nbclient import NotebookClient

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

results = []
for nb_path in notebooks:
    with open(nb_path) as f:
        nb = nbformat.read(f, as_version=4)
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
        # Print first line of error (keep output short)
        first_line = err.splitlines()[0] if err else ""
        print(f"  Error: {first_line[:100]}")

print(f"\n{n_pass}/{len(results)} notebook(s) passed.")
if n_pass < len(results):
    sys.exit(1)
