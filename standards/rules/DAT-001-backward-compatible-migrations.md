---
id: DAT-001
title: migrations and schema changes are backward compatible with the running version
status: approved
severity: high
check: review:data
---
Deploys are not atomic; old code runs against the new schema during rollout.
