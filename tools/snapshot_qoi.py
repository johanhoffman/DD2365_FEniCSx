#!/usr/bin/env python3
"""snapshot_qoi.py

Run course notebooks and capture named QoIs for a reproducible snapshot.

Commands
--------
run       Execute notebooks, write snapshot JSON (and optional markdown table).
compare   Compare two snapshot JSONs; exit 1 on drift beyond --rtol.

Usage
-----
    # FAST mode (CI baseline — T=0.2, plot_freq=2):
    conda run -n fenicsx-0.11-py312 python tools/snapshot_qoi.py run --fast \\
          --out tools/baseline_fast_ci.json

    # Full mode (default parameters):
    conda run -n fenicsx-0.11-py312 python tools/snapshot_qoi.py run \\
          --out /tmp/snapshot_full.json --md

    # Regression guard:
    python tools/snapshot_qoi.py compare tools/baseline_fast_ci.json new.json --rtol 1e-6

QoI extraction
--------------
Each notebook's code cells are scanned for lines of the form::

    QOI <name> = <value>

Only those named values are stored.  All other output (timings, cell counts,
mesh IDs, etc.) is ignored.

Canonical versions
------------------
Parsed per-notebook from ``# --- canonical: <name> vN ---`` markers
actually present in each notebook.

Snapshot JSON schema
--------------------
{
  "_meta": {
    "env": str, "python_version": str, "commit": str,
    "lockfile_sha256_prefix": str, "timestamp": str, "mode": str
  },
  "<notebook.ipynb>": {
    "status": "PASS" | "FAIL",
    "elapsed": float,
    "code_cells": int,
    "qois": {"<name>": float, ...},          # named QoIs only
    "canonical": {"<block>": "vN", ...},      # per-notebook canonical versions
    "error": str                              # only on FAIL
  },
  ...
}
"""

import sys, os, re, json, time, hashlib, pathlib, argparse, subprocess
import nbformat
from nbclient import NotebookClient

os.environ.setdefault("MPLBACKEND", "Agg")

FAST_OVERRIDE_SOURCE = "T = 0.2\nplot_freq = 2\n"
QOI_RE = re.compile(r"^QOI\s+(\S+)\s*=\s*(-?[\d.eE+\-]+)\s*$")
CANONICAL_RE = re.compile(r"#\s*---\s*canonical:\s*(\S+)\s*v(\d+)\s*---")
repo_root = pathlib.Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _extract_qois(cell_outputs_text: str) -> dict:
    """Return {name: float} for every 'QOI <name> = <value>' line."""
    qois = {}
    for line in cell_outputs_text.splitlines():
        m = QOI_RE.match(line.strip())
        if m:
            qois[m.group(1)] = float(m.group(2))
    return qois


def _cell_outputs_text(cell) -> str:
    parts = []
    for out in cell.get("outputs", []):
        if out.get("output_type") == "stream":
            parts.append("".join(out.get("text", [])))
        elif out.get("output_type") in ("execute_result", "display_data"):
            parts.append("".join(out.get("data", {}).get("text/plain", [])))
    return "\n".join(parts)


def _notebook_canonical_versions(nb) -> dict:
    """Parse canonical block markers from every source cell of a notebook."""
    versions = {}
    for cell in nb.cells:
        for m in CANONICAL_RE.finditer(cell.get("source", "")):
            versions[m.group(1)] = f"v{m.group(2)}"
    return versions


def _inject_fast(nb):
    param_idx = None
    for i, cell in enumerate(nb.cells):
        if "parameters" in cell.get("metadata", {}).get("tags", []):
            param_idx = i
    if param_idx is None:
        return nb
    nb.cells.insert(param_idx + 1, nbformat.v4.new_code_cell(source=FAST_OVERRIDE_SOURCE))
    return nb


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root,
            capture_output=True, text=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def _lockfile_hash() -> str:
    lockfile = repo_root / "env-osx-arm64.lock"
    if not lockfile.exists():
        return "none"
    return hashlib.sha256(lockfile.read_bytes()).hexdigest()[:16]


def _env_info() -> dict:
    env_name = os.environ.get("CONDA_DEFAULT_ENV", "unknown")
    try:
        py_ver = subprocess.run(
            ["python", "--version"], capture_output=True, text=True,
        ).stdout.strip().replace("Python ", "")
    except Exception:
        py_ver = sys.version.split()[0]
    return {"env": env_name, "python_version": py_ver}


# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------

def cmd_run(args):
    mode = "fast" if args.fast else "full"
    notebooks = sorted(repo_root.glob("*.ipynb"))
    if args.patterns:
        notebooks = []
        for pat in args.patterns:
            notebooks.extend(sorted(repo_root.glob(pat)))

    meta = {
        **_env_info(),
        "commit": _git_commit(),
        "lockfile_sha256_prefix": _lockfile_hash(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": mode,
    }
    results = {"_meta": meta}

    for nb_path in notebooks:
        with open(nb_path) as f:
            nb = nbformat.read(f, as_version=4)
        canonical = _notebook_canonical_versions(nb)
        if mode == "fast":
            nb = _inject_fast(nb)
        cell_count = len([c for c in nb.cells if c["cell_type"] == "code"])
        t0 = time.time()
        try:
            client = NotebookClient(
                nb, timeout=args.timeout, kernel_name="python3",
                allow_errors=False,
            )
            client.execute()
            elapsed = time.time() - t0
            qois = {}
            for cell in nb.cells:
                text = _cell_outputs_text(cell)
                if text:
                    qois.update(_extract_qois(text))
            results[nb_path.name] = {
                "status": "PASS",
                "elapsed": elapsed,
                "code_cells": cell_count,
                "qois": qois,
                "canonical": canonical,
            }
            qoi_str = "  ".join(f"{k}={v:.6g}" for k, v in qois.items())
            print(f"PASS  {nb_path.name:<48} {elapsed:6.1f}s  {qoi_str}", flush=True)
        except Exception as exc:
            elapsed = time.time() - t0
            results[nb_path.name] = {
                "status": "FAIL",
                "elapsed": elapsed,
                "code_cells": cell_count,
                "qois": {},
                "canonical": canonical,
                "error": str(exc)[:400],
            }
            print(f"FAIL  {nb_path.name:<48} {elapsed:6.1f}s  {str(exc)[:80]}", flush=True)

    out_path = pathlib.Path(args.out)
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nSnapshot written to {out_path}")
    if args.md:
        _print_markdown_table(results)


def _print_markdown_table(results):
    meta = results.get("_meta", {})
    env = meta.get("env", "?")
    py = meta.get("python_version", "?")
    commit = meta.get("commit", "?")[:8]
    lock = meta.get("lockfile_sha256_prefix", "?")
    mode = meta.get("mode", "?")
    ts = meta.get("timestamp", "?")

    print(f"\n## Snapshot — {mode} mode")
    print(f"\nEnv: `{env}` (Python {py}), commit `{commit}`, lockfile `{lock}`, {ts}\n")
    print(f"| Notebook | Cells | Status | Elapsed (s) | QoIs |")
    print(f"|---|---|---|---|---|")
    for nb_name, data in sorted(results.items()):
        if nb_name.startswith("_"):
            continue
        status = data.get("status", "?")
        cells = data.get("code_cells", "?")
        elapsed = data.get("elapsed", 0.0)
        qois = data.get("qois", {})
        qoi_str = ", ".join(f"{k}={v:.6g}" for k, v in qois.items()) if qois else "—"
        print(f"| `{nb_name}` | {cells} | {status} | {elapsed:.1f} | {qoi_str} |")


# ---------------------------------------------------------------------------
# compare command
# ---------------------------------------------------------------------------

def cmd_compare(args):
    d1 = json.loads(pathlib.Path(args.file1).read_text())
    d2 = json.loads(pathlib.Path(args.file2).read_text())
    m1, m2 = d1.get("_meta", {}), d2.get("_meta", {})

    print(f"Baseline: {m1.get('env')} py{m1.get('python_version')}  "
          f"commit {m1.get('commit','?')[:8]}  mode={m1.get('mode','?')}")
    print(f"Current:  {m2.get('env')} py{m2.get('python_version')}  "
          f"commit {m2.get('commit','?')[:8]}  mode={m2.get('mode','?')}")
    print()

    rtol = args.rtol
    all_nbs = sorted(k for k in d1 if not k.startswith("_"))
    max_reldiff = 0.0
    violations = []
    rows = []

    for nb in all_nbs:
        if nb not in d2:
            print(f"MISSING in current: {nb}")
            violations.append((nb, "MISSING", None, None, None))
            continue
        r1, r2 = d1[nb], d2[nb]
        if r1["status"] != "PASS" or r2["status"] != "PASS":
            rows.append((nb, "FAIL", "-"))
            continue
        q1 = r1.get("qois", {})
        q2 = r2.get("qois", {})
        nb_max = 0.0
        for name in q1:
            if name not in q2:
                print(f"  QOI missing in current: {nb}::{name}")
                continue
            v1, v2 = q1[name], q2[name]
            denom = max(abs(v1), abs(v2), 1e-300)
            rd = abs(v1 - v2) / denom
            if rd > nb_max:
                nb_max = rd
            if rd > max_reldiff:
                max_reldiff = rd
            if rd > rtol:
                violations.append((nb, name, v1, v2, rd))
        rows.append((nb, "PASS", f"{nb_max:.2e}"))

    w = 48
    print(f"{'Notebook':<{w}} {'Status':<8} {'MaxRelDiff':>12}")
    print("-" * (w + 22))
    for nb, status, mrd in rows:
        flag = ""
        if mrd != "-":
            try:
                if float(mrd) > rtol:
                    flag = " <-- DRIFT"
            except ValueError:
                pass
        print(f"{nb:<{w}} {status:<8} {mrd:>12}{flag}")

    print(f"\nOverall max reldiff: {max_reldiff:.3e}  (rtol: {rtol:.0e})")
    if violations:
        print(f"\nDRIFT VIOLATIONS ({len(violations)}):")
        for nb, name, v1, v2, rd in violations[:20]:
            if v1 is None:
                print(f"  {nb}: {name}")
            else:
                print(f"  {nb}::{name}: {v1} vs {v2}  reldiff={rd:.3e}")
        sys.exit(1)
    else:
        print("PASS — all QoIs within rtol.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

parser = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
sub = parser.add_subparsers(dest="cmd")

run_p = sub.add_parser("run", help="Execute notebooks and save snapshot")
run_p.add_argument("--fast", action="store_true",
                   help="Inject T=0.2, plot_freq=2 (CI mode)")
run_p.add_argument("--out", required=True, help="Output JSON path")
run_p.add_argument("--md", action="store_true", help="Also print markdown table")
run_p.add_argument("--timeout", type=int, default=600,
                   help="Per-notebook timeout in seconds (default 600)")
run_p.add_argument("patterns", nargs="*",
                   help="Glob patterns relative to repo root (default: *.ipynb)")

cmp_p = sub.add_parser("compare", help="Regression guard: compare two snapshots")
cmp_p.add_argument("file1", help="Baseline snapshot JSON")
cmp_p.add_argument("file2", help="Current snapshot JSON")
cmp_p.add_argument("--rtol", type=float, default=1e-6,
                   help="Relative tolerance for QoI drift (default 1e-6)")

args = parser.parse_args()
if args.cmd is None:
    parser.print_help()
    sys.exit(1)

if args.cmd == "run":
    cmd_run(args)
elif args.cmd == "compare":
    cmd_compare(args)
