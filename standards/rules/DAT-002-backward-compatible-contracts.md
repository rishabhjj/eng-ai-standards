---
id: DAT-002
title: public API and event contracts stay backward compatible: no removed or renamed fields, no new required inputs, no changed enum meaning without a version
status: approved
severity: high
check: review:data
---
Consumers deploy on their own schedule; a breaking contract change fails them without a diff in their repo.
