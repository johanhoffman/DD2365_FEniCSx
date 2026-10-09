#!/usr/bin/env python3
"""regression_qoi.py

Execute all notebooks in FAST mode and capture numeric outputs for env-to-env comparison.

Usage:
    conda run -n <env> python tools/regression_qoi.py --out results_<env>.json
    python tools/regression_qoi.py --compare results_env1.json results_env2.json

Outputs a JSON file: {notebook_name: {cell_index: [floats]}} plus metadata.
"""
import sys, os, re, json, time, pathlib, argparse
import nbformat
from nbclient import NotebookClient

os.environ.setdefault("MPLBACKEND", "Agg")

FAST_OVERRIDE_SOURCE = "T = 0.2\nplot_freq = 2\n"
FLOAT_RE = re.compile(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")

repo_root = pathlib.Path(__file__).parent.parent

parser = argparse.ArgumentParser(description=__doc__)
sub = parser.add_subparsers(dest="cmd")

run_p = sub.add_parser("run", help="Execute notebooks and save QoIs")
run_p.add_argument("--out", required=True, help="Output JSON file path")
run_p.add_argument("--timeout", type=int, default=600)
run_p.add_argument("patterns", nargs="*")

cmp_p = sub.add_parser("compare", help="Compare two QoI JSON files")
cmp_p.add_argument("file1")
cmp_p.add_argument("file2")
cmp_p.add_argument("--gate", type=float, default=1e-8)

# support legacy two-positional invocation for backward compat
args = parser.parse_args()
if args.cmd is None:
    parser.print_help()
    sys.exit(1)


def _extract_floats(text):
    return [float(m) for m in FLOAT_RE.findall(text) if m not in ("", ".")]


def _inject_fast(nb):
    param_idx = None
    for i, cell in enumerate(nb.cells):
        if "parameters" in cell.get("metadata", {}).get("tags", []):
            param_idx = i
    if param_idx is None:
        return nb
    nb.cells.insert(param_idx + 1, nbformat.v4.new_code_cell(source=FAST_OVERRIDE_SOURCE))
    return nb


if args.cmd == "run":
    import subprocess
    env_name = subprocess.run(
        ["conda", "run", "--no-capture-output", "python", "-c", "import sys; print(sys.prefix)"],
        capture_output=True, text=True,
    ).stdout.strip().split("/")[-1] if False else os.environ.get("CONDA_DEFAULT_ENV", "unknown")

    if args.patterns:
        notebooks = []
        for pat in args.patterns:
            notebooks.extend(sorted(repo_root.glob(pat)))
    else:
        notebooks = sorted(repo_root.glob("*.ipynb"))

    results = {"_meta": {"env": env_name, "commit": None, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}}
    try:
        import subprocess as _sp
        results["_meta"]["commit"] = _sp.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True,
        ).stdout.strip()
    except Exception:
        pass

    for nb_path in notebooks:
        with open(nb_path) as f:
            nb = nbformat.read(f, as_version=4)
        nb = _inject_fast(nb)
        t0 = time.time()
        try:
            client = NotebookClient(nb, timeout=args.timeout, kernel_name="python3",
                                    allow_errors=False)
            client.execute()
            elapsed = time.time() - t0
            cell_floats = {}
            for i, cell in enumerate(nb.cells):
                for out in cell.get("outputs", []):
                    text = ""
                    if out.get("output_type") == "stream":
                        text = "".join(out.get("text", []))
                    elif out.get("output_type") in ("execute_result", "display_data"):
                        text = "".join(out.get("data", {}).get("text/plain", []))
                    if text:
                        floats = _extract_floats(text)
                        if floats:
                            cell_floats[str(i)] = floats
            results[nb_path.name] = {"status": "PASS", "elapsed": elapsed, "cells": cell_floats}
            print(f"PASS {nb_path.name}  ({elapsed:.1f}s)")
        except Exception as exc:
            elapsed = time.time() - t0
            results[nb_path.name] = {"status": "FAIL", "elapsed": elapsed, "error": str(exc)[:400]}
            print(f"FAIL {nb_path.name}  ({elapsed:.1f}s): {str(exc)[:200]}")

    out_path = pathlib.Path(args.out)
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nResults written to {out_path}")

elif args.cmd == "compare":
    d1 = json.loads(pathlib.Path(args.file1).read_text())
    d2 = json.loads(pathlib.Path(args.file2).read_text())
    meta1, meta2 = d1.get("_meta", {}), d2.get("_meta", {})
    print(f"Env 1: {meta1.get('env')}  commit {meta1.get('commit', '?')[:8]}")
    print(f"Env 2: {meta2.get('env')}  commit {meta2.get('commit', '?')[:8]}")
    print()

    all_nbs = sorted(k for k in d1 if not k.startswith("_"))
    max_reldiff = 0.0
    gate = args.gate
    violations = []
    rows = []

    for nb in all_nbs:
        if nb not in d2:
            print(f"MISSING in file2: {nb}")
            continue
        r1, r2 = d1[nb], d2[nb]
        if r1["status"] != "PASS" or r2["status"] != "PASS":
            rows.append((nb, "FAIL/FAIL", "-", "-"))
            continue
        nb_max = 0.0
        for cell_idx in r1["cells"]:
            if cell_idx not in r2["cells"]:
                continue
            f1s, f2s = r1["cells"][cell_idx], r2["cells"][cell_idx]
            if len(f1s) != len(f2s):
                continue
            for v1, v2 in zip(f1s, f2s):
                denom = max(abs(v1), abs(v2), 1e-300)
                rd = abs(v1 - v2) / denom
                if rd > nb_max:
                    nb_max = rd
                if rd > max_reldiff:
                    max_reldiff = rd
                if rd > gate:
                    violations.append((nb, cell_idx, v1, v2, rd))
        rows.append((nb, "PASS/PASS", f"{nb_max:.2e}", ""))

    print(f"{'Notebook':<44} {'Status':<12} {'MaxRelDiff':>12}")
    print("-" * 72)
    for nb, status, mrd, _ in rows:
        flag = " <-- GATE" if mrd != "-" and float(mrd.replace("e", "e")) > gate else ""
        print(f"{nb:<44} {status:<12} {mrd:>12}{flag}")

    print(f"\nOverall max relative diff: {max_reldiff:.3e}  (gate: {gate:.0e})")
    if violations:
        print(f"\nVIOLATIONS ({len(violations)}):")
        for nb, ci, v1, v2, rd in violations[:20]:
            print(f"  {nb} cell {ci}: {v1} vs {v2}  reldiff={rd:.3e}")
        if max_reldiff > gate:
            sys.exit(1)
    else:
        print("GATE: PASS — all relative diffs within tolerance.")
