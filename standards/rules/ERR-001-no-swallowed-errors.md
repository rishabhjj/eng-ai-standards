---
id: ERR-001
title: no empty catch, bare except or ignored error results
status: approved
severity: high
check: semgrep:lint-packs/semgrep/ERR-001-swallowed-errors.yml, linter:ruff:BLE001, linter:detekt:EmptyCatchBlock, linter:eslint:no-empty, review:correctness
---
Silent failure turns a visible bug into data loss.
