---
id: COD-005
title: money uses decimal types, never floating point
status: approved
severity: high
check: review:correctness
---
Binary floats cannot represent cents and accumulate rounding error.
