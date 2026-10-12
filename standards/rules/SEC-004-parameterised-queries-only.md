---
id: SEC-004
title: no string-built SQL, shell, HTML or templates
status: approved
severity: critical
check: semgrep:lint-packs/semgrep/SEC-004-injection.yml, linter:ruff:S608, review:security
---
Concatenating input into an interpreter is injection; parameters and escaping APIs remove the class.
