# Lens: simplicity (anti-bloat)

Rules applied: COD-001 COD-002 COD-003 COD-004 DEP-001. Cite the ID on every finding it covers.

One finding per cut: location, what to remove, what replaces it.
- **COD-001:** interface with one impl, factory for one product, generic param used once, config for a constant, pass-through layers with no logic.
- **COD-002, DEP-001:** new dependency. Could stdlib, the platform or an installed dependency do it in under 20 lines? Grep the repo for an existing helper first. It must be pinned in the committed lockfile with an allow-listed licence, and not a typo-squat or a package with install scripts.
- **COD-003:** dead or unreachable code, unused exports, commented-out code, flags that never flip.
- **COD-004:** comments that restate the code or run past 2 lines.
- Diff scope: unrelated refactors or formatting churn mixed into the change.

## What NOT to flag
- Validation at trust boundaries, security checks, error handling that prevents data loss, accessibility.
- Abstractions that already have two or more real users.
- Anything the author was explicitly asked to build.
