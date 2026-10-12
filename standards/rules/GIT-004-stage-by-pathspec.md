---
id: GIT-004
title: stage explicit paths, never git add -A or .
status: enforced
severity: medium
check: hook:.claude/hooks/guard-bash.sh
---
Bulk staging sweeps in secrets, build output and unrelated work.
