---
id: SEC-002
title: never hand-edit .env, keys or lockfiles
status: enforced
severity: high
check: hook:.claude/hooks/protect-files.sh
---
Secret files must not enter agent context or diffs; lockfiles are generated and hand edits corrupt resolution.
