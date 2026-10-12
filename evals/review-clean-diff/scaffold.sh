#!/usr/bin/env bash
set -euo pipefail
git init -q -b main .
git config user.email e@e && git config user.name e
mkdir app tests
touch app/__init__.py tests/__init__.py
cat > app/pricing.py <<'PY'
from decimal import Decimal


def total(prices: list[Decimal]) -> Decimal:
    t = Decimal("0")
    for p in prices:
        t += p
    return t
PY
cat > tests/test_pricing.py <<'PY'
import unittest
from decimal import Decimal

from app.pricing import total


class TotalTest(unittest.TestCase):
    def test_sums_prices(self):
        self.assertEqual(total([Decimal("1.10"), Decimal("2.20")]), Decimal("3.30"))

    def test_empty_is_zero(self):
        self.assertEqual(total([]), Decimal("0"))
PY
git add . && git commit -qm "chore: base"
git checkout -qb refactor/total
cat > app/pricing.py <<'PY'
from decimal import Decimal


def total(prices: list[Decimal]) -> Decimal:
    return sum(prices, Decimal("0"))
PY
git add . && git commit -qm "refactor: simplify total with sum"
git diff main...HEAD > changes.diff
