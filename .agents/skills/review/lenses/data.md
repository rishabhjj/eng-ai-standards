# Lens: data, contracts and performance

Run only when the diff touches migrations, schemas, serialization, public APIs, queries or hot paths.
Rules applied: DAT-001 DAT-002 OPS-002. Cite the ID on every finding it covers.

- **DAT-001:** during rollout old code runs against the new schema and new code against the old. Flag dropped or renamed columns, new NOT NULL without default, type changes, and changes that need a lock on a large table.
- **API and event contracts (DAT-002):** removed or renamed fields, changed types or status codes, new required inputs, changed enum meanings, all without a new version.
- **Idempotency (OPS-002):** a consumer, job or webhook handler that writes must survive at-least-once delivery: dedupe key, upsert or a unique constraint on the delivery id.
- **Serialization:** persisted formats read by older versions, polymorphic type changes.
- **Performance:** N+1 queries, unbounded result sets, missing indexes for new filters, IO inside loops, accidental O(n^2), new unbounded caches.

## What NOT to flag
- Micro-optimisations off any hot path.
- Index suggestions without a query in the diff that needs one.
- Contract changes to internal-only types with no external consumer.
