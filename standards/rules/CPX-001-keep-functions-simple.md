---
id: CPX-001
title: functions stay under a cyclomatic complexity of 10
status: approved
severity: low
check: linter:ruff:C901, linter:eslint:complexity, linter:detekt:CyclomaticComplexMethod
---
Branch-heavy functions hide bugs and resist testing; splitting them is cheaper than debugging them.
