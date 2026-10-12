---
name: review-spec
description: Review a design doc, spec or plan against the team standards before any code is written. Use whenever the user asks to review, check or critique a plan, design or spec, and after drafting a plan for a change touching more than 3 files.
---

# Review a spec

Input: a spec or design doc (path or pasted text). Read it fully, then read the rules index in `AGENTS.md` and the files in `standards/rules/` that apply at design time.

Report only problems you can tie to a concrete scenario in which the design fails. No scenario, no finding.

## Check
- **Goal and scope:** a one-sentence goal, explicit non-goals, and the smallest design that meets the goal. Flag speculative flexibility, a new dependency without a justification (COD-002), or an abstraction with one user (COD-001).
- **Acceptance criteria:** each is testable by a named test or observable outcome (TST-001). Flag criteria no one could verify.
- **Failure modes:** what happens on timeout, partial failure, retries and bad input; no error is silently dropped (ERR-001).
- **Data and rollout:** migrations and schema changes work while old and new code run together (DAT-001); rollout order and rollback are stated; money uses decimal types (COD-005).
- **Security:** who may do what is stated and checked server-side (SEC-003); every external input has a validation boundary (COD-006); secrets and PII are named with where they live and that they never reach logs (SEC-001, SEC-005); untrusted content is treated as data (SEC-006).
- **Evidence:** how a reviewer will see it work (tests, logs, a screenshot).
- **Open questions:** decisions the author deferred that block implementation.

## Output
`Blockers`, `Should fix`, `Open questions`. Each finding: the section it concerns, the failing scenario, a fix, and the rule ID when one applies. Zero findings is a valid result. Do not edit the spec.
