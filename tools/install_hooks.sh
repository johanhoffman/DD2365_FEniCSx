#!/usr/bin/env bash
# tools/install_hooks.sh — install git pre-commit hook for this repo.
#
# Run once from the repo root:
#   bash tools/install_hooks.sh
#
# The hook runs two checks on every commit:
#   1. check_canonical.py — verifies notebook canonical blocks match canonical/*.py
#   2. nbstripout         — strips outputs/metadata from staged *.ipynb files
#      (notebooks are committed without outputs; run `jupyter nbconvert --to notebook
#       --execute` or `tools/run_notebooks.py` to regenerate outputs locally)
#
# Requirements:
#   - Python 3 with nbstripout installed (conda env fenicsx-0.11 or `pip install nbstripout`)
#   - Run from the repo root (the script resolves paths relative to the .git dir)

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="$REPO_ROOT/.git/hooks/pre-commit"

# Resolve nbstripout: prefer the fenicsx-0.11 conda env, fall back to PATH.
NBSTRIPOUT_BIN="$(conda run -n fenicsx-0.11 which nbstripout 2>/dev/null || which nbstripout 2>/dev/null || echo '')"
if [ -z "$NBSTRIPOUT_BIN" ]; then
    echo "WARNING: nbstripout not found — hook will skip output stripping."
    echo "Install with: conda install -n fenicsx-0.11 nbstripout"
    NBSTRIPOUT_BIN="nbstripout"  # let the hook fail loudly if called
fi

cat > "$HOOK" << HOOK_EOF
#!/usr/bin/env bash
# pre-commit: check canonical blocks and strip notebook outputs.
set -euo pipefail

REPO_ROOT="\$(git rev-parse --show-toplevel)"
NBSTRIPOUT="${NBSTRIPOUT_BIN}"

# 1. Verify canonical blocks in staged notebooks
if git diff --cached --name-only | grep -q '\.ipynb\$'; then
    python3 "\$REPO_ROOT/tools/check_canonical.py" || {
        echo "ABORT: canonical block mismatch. Fix drift before committing."
        exit 1
    }
fi

# 2. Strip outputs from staged *.ipynb files
STAGED_NBS=\$(git diff --cached --name-only --diff-filter=ACM | grep '\.ipynb\$' || true)
if [ -n "\$STAGED_NBS" ]; then
    for nb in \$STAGED_NBS; do
        "\$NBSTRIPOUT" "\$REPO_ROOT/\$nb"
        git add "\$REPO_ROOT/\$nb"
    done
fi
HOOK_EOF

chmod +x "$HOOK"
echo "Installed pre-commit hook at $HOOK"
echo "  nbstripout: $NBSTRIPOUT_BIN"
