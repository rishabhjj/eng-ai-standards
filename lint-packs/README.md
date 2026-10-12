# Lint packs

Base configs that back the `linter:` and `semgrep:` checks in `standards/rules/`. `bootstrap` copies the packs for a repo's detected languages (plus `semgrep/`) into `.eng-ai/lint/`, which is kit-owned. A repo extends them from its own config, so its own overrides win:

| Language | Base file | Extend it with |
|---|---|---|
| Python | `python/ruff.toml`, `python/mypy.ini` | `extend = ".eng-ai/lint/python/ruff.toml"` |
| TypeScript | `typescript/eslint.config.mjs`, `typescript/tsconfig.strict.json` | import the base array in `eslint.config.mjs`, `"extends"` in tsconfig |
| Kotlin | `kotlin/detekt.yml` | `config.setFrom(files(".eng-ai/lint/kotlin/detekt.yml", "config/detekt.yml"))` |
| Java | `java/errorprone.md` | copy the snippets into the Gradle build |
| All | `semgrep/*.yml` | `semgrep --metrics=off --config .eng-ai/lint/semgrep .` |

Every config names the rule ID it serves in a comment. `scripts/standards-check.py` fails if a rule points at a linter setting that no pack contains, or a pack file that does not cite the ID.

**Status**

| Pack | Verified against the real tool |
|---|---|
| `semgrep/` | Yes: semgrep 1.180.0, `scripts/test-semgrep-rules.sh` runs annotated fixtures in `semgrep-tests/` (rule fires, and safe code does not) |
| `python/ruff.toml` | Yes: ruff 0.17.0, every referenced code fires on a sample file; `S603`/`S607` are ignored because they flag the safe list-form call. `S113` (OPS-001) and `T20` (OBS-001) were added after that run and are not yet exercised |
| `python/mypy.ini` | Yes: mypy 2.4.0 flags untyped defs and `Any` returns, clean code passes |
| `typescript/eslint.config.mjs` | Yes: ESLint 10.12.0 + typescript-eslint 8.71.1, laid out as `bootstrap` installs it. `no-explicit-any`, `no-non-null-assertion`, `no-empty`, `no-eval`, `no-new-func`, `complexity` fire. `no-console` (OBS-001) was added after that run and is not yet exercised. `no-implied-eval` did not fire on `setTimeout("...")` in the sample (core rule needs environment globals) |
| `typescript/tsconfig.strict.json` | Yes: tsc 6.0.3 reports implicit `any` and `string \| undefined` from indexing |
| `kotlin/detekt.yml` | Partly: detekt 1.23.8 CLI loads it and fires `CyclomaticComplexMethod`, `EmptyCatchBlock`, `SwallowedException`. `UnsafeCallOnNullableType` and `UnsafeCast` need type resolution (Gradle `detektMain`) and are not exercised |
| `java/errorprone.md` | No |

Known semgrep gaps: Kotlin has only the empty-catch rule (no SQL rules), and the rules are intraprocedural patterns, so they will not follow a string built elsewhere and passed in.

Rules stay `approved` (reported, not blocking) until the packs have run on the pilot repos and the violation counts are known.

Legacy repos: generate a baseline first (`ruff --add-noqa`, `detekt --create-baseline`, `eslint --suppress-all`) so only new code is held to the rules.
