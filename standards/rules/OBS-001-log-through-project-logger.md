---
id: OBS-001
title: production code logs through the project logger with context, never print/console; a handled error is logged once
status: approved
severity: medium
check: linter:ruff:T201, linter:eslint:no-console, review:correctness
---
print and console bypass levels, structure and shipping, and an error logged at every layer buries the real signal.
