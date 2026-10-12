# Lens: tests

Rules applied: TST-001 TST-003. Cite the ID on every finding it covers.

- **TST-001:** does each behaviour change have a test for the new behaviour and its error or edge path? For a bug fix, would the new test fail on the old code? Name the line the test would catch.
- **TST-003:** tests that only assert a mock was called, mirror the implementation, or pass with the code deleted.
- Flaky patterns: sleeps, shared global state, order dependence, real clocks or network.
- Duplicate tests that add no coverage.

## What NOT to flag
- Missing tests for pure refactors with unchanged behaviour and existing coverage.
- Coverage percentages. Judge by behaviours covered, not by lines.
- Test style preferences.
