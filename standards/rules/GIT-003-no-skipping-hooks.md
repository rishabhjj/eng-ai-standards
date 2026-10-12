---
id: GIT-003
title: never use --no-verify or skip signing
status: enforced
severity: high
check: hook:.claude/hooks/guard-bash.sh
---
Hooks are the deterministic gate; bypassing them defeats every other rule.
