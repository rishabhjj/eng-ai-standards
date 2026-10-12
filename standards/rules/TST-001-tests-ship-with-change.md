---
id: TST-001
title: behaviour changes ship with tests covering the new behaviour and its error path; a bug fix includes a test that fails without the fix
status: approved
severity: high
check: review:tests
---
Untested changes regress silently; a test that fails without the fix proves the bug is real and the fix is the cause.
