#!/usr/bin/env bash
set -euo pipefail
git init -q -b main .
git config user.email e@e && git config user.name e
mkdir app
cat > app/payments.py <<'PY'
def charge(gateway, order):
    return gateway.charge(order.id, order.amount)
PY
git add . && git commit -qm "chore: base"
git checkout -qb feature/retry
cat > app/payments.py <<'PY'
def charge(gateway, order):
    try:
        return gateway.charge(order.id, order.amount)
    except Exception:
        pass
PY
git add . && git commit -qm "feat: make charge resilient"
git diff main...HEAD > changes.diff
