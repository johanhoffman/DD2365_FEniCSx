#!/usr/bin/env python3
"""check_canonical.py

Verify that every canonical block embedded in every notebook matches
the corresponding canonical/<name>.py file byte-for-byte.

Usage:
    python tools/check_canonical.py          # from repo root
    python tools/check_canonical.py -v       # verbose (show diffs)

Exit 0 if all blocks match; nonzero if any drift is found.
"""
import json, sys, pathlib, difflib, argparse, subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("-v", "--verbose", action="store_true")
args = parser.parse_args()

repo_root = pathlib.Path(__file__).parent.parent
canonical_dir = repo_root / "canonical"

def _tracked_or_staged(path):
    """Return True if path is tracked by git or currently staged."""
    r = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        cwd=repo_root, capture_output=True,
    )
    if r.returncode == 0:
        return True
    r2 = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo_root, capture_output=True, text=True,
    )
    return path.name in r2.stdout

notebooks = [
    p for p in
    sorted(repo_root.glob("*.ipynb")) + sorted((repo_root / "verification").glob("*.ipynb"))
    if _tracked_or_staged(p)
]

errors = []
checked = 0

for nb_path in notebooks:
    with open(nb_path) as f:
        nb = json.load(f)

    # Verify bootstrap is the first code cell (allowing one leading comment-only header cell)
    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    if code_cells:
        first_src = "".join(code_cells[0].get("source", []))
        is_comment_only = all(
            ln.startswith("#") or not ln.strip()
            for ln in first_src.splitlines()
        )
        candidate_idx = 1 if is_comment_only and len(code_cells) > 1 else 0
        candidate_src = "".join(code_cells[candidate_idx].get("source", []))
        if "# --- canonical: bootstrap" not in candidate_src:
            errors.append(
                f"{nb_path.name}: bootstrap canonical block is not the first "
                f"(or second, after a comment-only header) code cell"
            )

    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        lines = source.splitlines(keepends=True)
        i = 0
        while i < len(lines):
            line = lines[i].rstrip("\n")
            if not line.startswith("# --- canonical:"):
                i += 1
                continue
            parts = line.split()
            # format: # --- canonical: <name> v<N> ---
            # parts = ['#', '---', 'canonical:', '<name>', 'v<N>', '---']
            if len(parts) < 5:
                i += 1
                continue
            name = parts[3]
            start = i + 1
            j = start
            end_marker = f"# --- end canonical: {name} ---"
            while j < len(lines) and lines[j].rstrip("\n") != end_marker:
                j += 1
            block_content = "".join(lines[start:j])
            canonical_file = canonical_dir / f"{name}.py"
            if not canonical_file.exists():
                errors.append(f"{nb_path.name}: canonical file not found: canonical/{name}.py")
                i = j + 1
                continue
            expected = canonical_file.read_text()
            if block_content != expected:
                errors.append(
                    f"{nb_path.name}: block '{name}' differs from canonical/{name}.py"
                )
                if args.verbose:
                    diff = list(difflib.unified_diff(
                        expected.splitlines(keepends=True),
                        block_content.splitlines(keepends=True),
                        fromfile=f"canonical/{name}.py",
                        tofile=f"{nb_path.name}::{name}",
                    ))
                    print("".join(diff))
            else:
                checked += 1
            i = j + 1

if errors:
    for e in errors:
        print(f"FAIL: {e}")
    sys.exit(1)
print(f"OK: {checked} canonical block(s) in {len(notebooks)} notebook(s) — all match.")
