---
id: TYP-001
title: no untyped escape hatches (any, !!, unchecked casts) outside boundaries
status: approved
severity: medium
check: linter:eslint:@typescript-eslint/no-explicit-any, linter:detekt:UnsafeCallOnNullableType, linter:tsc:strict, linter:mypy:strict, linter:errorprone:NullAway
---
Escape hatches switch off the type checker exactly where bugs hide; boundaries validate once and then types hold.
