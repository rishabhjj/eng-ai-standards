---
id: SEC-008
title: no eval, dynamic code or unsafe deserialization of untrusted data
status: approved
severity: critical
check: semgrep:lint-packs/semgrep/SEC-008-dynamic-eval.yml, linter:ruff:S307, linter:eslint:no-eval, review:security
---
Evaluating or deserializing attacker-influenced data executes attacker-chosen code.
