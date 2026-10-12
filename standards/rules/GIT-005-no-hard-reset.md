---
id: GIT-005
title: no git reset --hard or git clean -f without approval
status: enforced
severity: high
check: hook:.claude/hooks/guard-bash.sh
---
Destroys uncommitted work irrecoverably.
