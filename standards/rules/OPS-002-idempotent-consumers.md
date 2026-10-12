---
id: OPS-002
title: jobs, consumers and webhooks are idempotent under at-least-once delivery (dedupe key or upsert)
status: approved
severity: high
check: review:correctness, review:data
---
Queues and webhook senders redeliver; a handler that is not idempotent double-charges, double-sends or corrupts state.
