---
id: SEC-001
title: no secrets in code, logs, tests or prompts
status: enforced
severity: critical
check: hook:.githooks/pre-commit, ci:.github/workflows/eng-ai-security.yml
---
A leaked key is exploitable the moment it is pushed; scanning at commit stops it before history is public.
