#!/usr/bin/env bash
set -euo pipefail
git init -q -b main .
git config user.email e@e && git config user.name e
cat > calc.py <<'PY'
def apply_discount(price, pct):
    return price - pct
PY
git add . && git commit -qm "chore: base"
