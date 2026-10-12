#!/usr/bin/env bash
# Run semgrep's own rule tests (annotated fixtures in lint-packs/semgrep-tests).
# Uses semgrep from PATH, else uvx. Skips with a clear message when neither exists.
cd "$(git rev-parse --show-toplevel)" || exit 1
if command -v semgrep >/dev/null 2>&1; then run=(semgrep)
elif command -v uvx >/dev/null 2>&1; then run=(uvx --from semgrep semgrep)
else echo "test-semgrep-rules: SKIPPED (semgrep and uvx not found)"; exit 0; fi
"${run[@]}" --test --metrics=off --disable-version-check --config lint-packs/semgrep lint-packs/semgrep-tests
