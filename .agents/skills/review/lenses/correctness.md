# Lens: correctness and errors

Rules applied: COD-005 ERR-001 OPS-001 OPS-002 OBS-001. Cite the ID on every finding it covers.

- **Boundaries:** off-by-one, inclusive vs exclusive ranges, empty/one/many, null/zero/negative. What input flips each new condition, and is the inverse branch handled?
- **Callers:** grep every caller of each changed signature or behaviour; do they still hold their assumptions?
- **State:** shared or aliased mutation, stale caches, ordering assumptions.
- **Idempotency (OPS-002):** a job, consumer or webhook handler delivered twice must not double-write, double-send or double-charge: dedupe key, upsert or idempotent write.
- **Network (OPS-001):** every outbound call has an explicit timeout and bounded retries with backoff; no retry of a non-idempotent call without a key.
- **Partial failure:** if step 2 of 3 fails, is data left half-written? Is rollback or compensation present?
- **Time and numbers:** timezones, DST, expiry comparisons (`<` vs `<=`), overflow, rounding, unit mixups. Money must be decimal (COD-005).
- **Errors (ERR-001):** empty catch, bare `except`, ignored error results, errors logged and then continued as success.
- **Logging (OBS-001):** `print` or `console.*` in production code, log lines without context (ids, operation), the same handled error logged at more than one layer.
- **Spec drift:** does the code do what the PR description says, including the unhappy path?

## What NOT to flag
- Style, naming or formatting. Linters own those.
- Hypothetical failures that need an impossible state. Give a concrete failing input or drop it.
- Behaviour that is intentional and documented in the PR description.
