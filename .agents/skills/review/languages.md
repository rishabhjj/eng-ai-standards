# Language and framework checks that linters cannot see

Read only the sections for languages in the diff. Each item names the rule it serves. Mechanical issues belong in the lint packs; this list is for judgment calls.

## Kotlin and Ktor
- Structured concurrency: no `GlobalScope`; a launched job has an owner and is cancelled with it.
- A `catch (e: Exception)` around suspending code must rethrow `CancellationException` (ERR-001).
- No blocking calls (JDBC, file IO, `Thread.sleep`) on `Dispatchers.Default` or inside a handler without `Dispatchers.IO`; `runBlocking` inside a request handler.
- Every route that touches user data sits inside an `authenticate { }` block and checks ownership, not just login (SEC-003).
- `BigDecimal("1.10")` from a string, never from a `Double` (COD-005).
- Request models are separate from persistence entities; sealed or polymorphic types have an explicit serializer (COD-006).

## Java and Spring
- Resources in try-with-resources; `equals` and `hashCode` change together; shared mutable state is thread-safe.
- `@Transactional` on a method called from the same class is not applied (proxy self-invocation); transaction boundaries match the unit of work.
- Entities are not returned from controllers; validate with Bean Validation at the boundary (COD-006).
- `Optional` as a field or parameter, `SimpleDateFormat` shared across threads, `new Random()` for tokens (SEC rules).

## TypeScript: NestJS
- Authentication guard is global or on every controller; authorization checks object ownership in the service (SEC-003).
- `ValidationPipe` with `whitelist: true` and `forbidNonWhitelisted: true`; every body, query and param has a DTO with class-validator decorators (COD-006).
- No business logic or raw queries in controllers; repositories use parameters or the query builder (SEC-004).
- Guards, interceptors and pipes run in a known order; a new interceptor must not swallow errors (ERR-001).

## TypeScript: Next.js
- Server actions and route handlers authenticate and authorize themselves. Middleware is not the only check (SEC-003).
- No secret in `NEXT_PUBLIC_*` or in a client component's props (SEC-005).
- Per-user data is never served from a shared cache; check `fetch` cache options, `revalidate`, and ISR on pages that read cookies.
- `dangerouslySetInnerHTML` only with sanitized input; server/client boundary: server-only modules are not imported by client components.

## TypeScript: Vite and frontend
- Nothing sensitive in `VITE_*`; they are inlined into the public bundle.
- Dev server is not exposed (`--host`) on shared networks; `server.fs.strict` stays on.
- Bundle budget: a new dependency states its size cost (COD-002).

## Python
- Mutable default arguments; naive `datetime` where timezone matters.
- Blocking calls (`requests`, file IO, `time.sleep`) inside `async def`; missing `await` on a coroutine.
- `except Exception` that logs and continues as success (ERR-001); `subprocess` with `shell=True` (SEC-004).
- pydantic: `model_construct` or `.dict()` bypassing validation on external input (COD-006); SQLAlchemy sessions closed on every path.
- `yaml.load`, `pickle.loads` or `eval` on data from outside the process (SEC-008).
