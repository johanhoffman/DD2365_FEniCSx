"""Verify every Colab badge URL in every notebook uses blob/main/<repo-relative-path>."""
import json
import re
import sys
from pathlib import Path

REPO = "johanhoffman/DD2365_FEniCSx"
BASE = f"https://colab.research.google.com/github/{REPO}/blob/main/"
BADGE_RE = re.compile(
    r"https://colab\.research\.google\.com/github/[^\s\"')>]+"
)

repo_root = Path(__file__).parent.parent
notebooks = sorted(
    list(repo_root.glob("*.ipynb")) + list(repo_root.glob("verification/*.ipynb"))
)

errors = []
for nb_path in notebooks:
    rel = nb_path.relative_to(repo_root)
    expected = BASE + str(rel)
    with open(nb_path) as f:
        data = json.load(f)
    for cell in data["cells"]:
        src = "".join(cell.get("source", []))
        for url in BADGE_RE.findall(src):
            if url != expected:
                errors.append(f"  {rel}: got {url!r}\n         want {expected!r}")

if errors:
    print("FAIL: badge URL mismatch in the following notebooks:")
    for e in errors:
        print(e)
    sys.exit(1)

print(f"OK: {len(notebooks)} notebook(s) — all badges point to blob/main/<path>")
