---
id: SEC-007
title: never pipe a remote script into a shell
status: enforced
severity: high
check: hook:.claude/hooks/guard-bash.sh
---
Runs unreviewed code with the user's privileges.
