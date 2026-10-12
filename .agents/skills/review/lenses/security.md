# Lens: security

Rules applied: SEC-003 SEC-004 SEC-005 SEC-006 SEC-008 COD-006. Cite the ID on every finding it covers.

Assume the attacker controls every input, header, file and upstream response.
- **AuthN/AuthZ (SEC-003):** every new route, handler, job or consumer enforces authz server-side; object-level checks (can user A read B's id?); tenant scoping on every query; default-deny.
- **Injection (SEC-004):** SQL/NoSQL/OS command/template/header/log injection; string-built queries; `shell=True`, `exec`, `eval`.
- **Logging (SEC-005):** PII, tokens, secrets in logs, URLs, errors or client bundles (`NEXT_PUBLIC_*`, `VITE_*`).
- **Dynamic code (SEC-008):** `eval`, `exec`, `new Function`, native deserialization of untrusted data.
- **Untrusted content (SEC-006):** user-controlled text reaching tool calls, prompts, paths or URLs; model output used as code, SQL or a path.
- **Boundaries (COD-006):** untyped request binding, mass assignment, unvalidated enums or polymorphic types.
- Also: SSRF and path traversal (allow-lists), XSS/CSRF/CORS, crypto misuse (homemade, weak hashes, `Math.random` tokens, JWT `alg:none`), unbounded input (ReDoS, uploads).

## What NOT to flag
- Theoretical issues with no reachable input path. Report only what is exploitable or concretely dangerous.
- Missing hardening already enforced by the framework or a gateway you can see in the code.
- Findings in tests, fixtures or example configs with obviously fake values.
