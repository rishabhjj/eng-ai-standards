---
id: OPS-001
title: every outbound network call has an explicit timeout and bounded retries with backoff
status: approved
severity: high
check: linter:ruff:S113, semgrep:lint-packs/semgrep/OPS-001-no-timeout.yml, review:correctness
---
A call with no timeout hangs a worker forever and unbounded retries turn one slow dependency into an outage.
