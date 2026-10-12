---
id: DEP-001
title: dependencies are pinned by a committed lockfile and carry an allow-listed licence
status: approved
severity: medium
check: review:simplicity
---
Unpinned dependencies make builds irreproducible and an unreviewed licence can taint the product; the Trivy licence scan in `.github/workflows/eng-ai-security.yml` is the planned deterministic check.
