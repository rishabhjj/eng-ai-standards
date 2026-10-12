#!/usr/bin/env bash
# One command for lint + types + tests + build. Override the detected steps with a
# "verify" list in .eng-ai.json. VERIFY_LIST=1 prints the steps without running them.
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

steps=()
if [ -f .eng-ai.json ]; then
  listed=$(python3 -I -c 'import json; print("\n".join(json.load(open(".eng-ai.json")).get("verify", [])))') || {
    echo "verify: .eng-ai.json is not valid JSON" >&2; exit 1; }
  while IFS= read -r line; do
    [ -n "$line" ] && steps+=("$line")
  done <<<"$listed"
fi

has_script() { grep -Eq "\"$1\"[[:space:]]*:" package.json; }

# Project files below the root mean a monorepo: auto-detection would only see the root.
nested_projects() {
  { git ls-files 2>/dev/null || find . -maxdepth 3 -type f | sed 's|^\./||'; } \
    | grep -E '/(pyproject\.toml|package\.json|gradlew|pom\.xml|go\.mod)$' | grep -v node_modules | head -n 3
}

if [ ${#steps[@]} -eq 0 ]; then
  nested=$(nested_projects | tr '\n' ' ')
  if [ -n "$nested" ]; then
    echo "verify: nested projects found (${nested% }); add a 'verify' list to .eng-ai.json" >&2
    exit 1
  fi
  if [ -f ./gradlew ]; then
    steps+=("sh ./gradlew -q check")
  elif [ -f pom.xml ]; then
    steps+=("mvn -q verify")
  fi
  if [ -f package.json ]; then
    pm=npm
    [ -f pnpm-lock.yaml ] && pm=pnpm
    [ -f yarn.lock ] && pm=yarn
    for s in lint typecheck test build; do has_script "$s" && steps+=("$pm run $s"); done
  fi
  if [ -f pyproject.toml ] || [ -f requirements.txt ] || [ -f setup.py ]; then
    if [ -f ruff.toml ] || [ -f .ruff.toml ] || grep -qs '^\[tool\.ruff' pyproject.toml; then steps+=("ruff check ."); fi
    if [ -f mypy.ini ] || grep -qs '^\[tool\.mypy' pyproject.toml || grep -qs '^\[mypy\]' setup.cfg; then steps+=("mypy ."); fi
    if [ -d tests ] || [ -d test ]; then
      if command -v pytest >/dev/null 2>&1; then steps+=("pytest -q")
      else steps+=("python3 -m unittest discover -s $([ -d tests ] && echo tests || echo test)"); fi
    fi
  fi
fi

if [ ${#steps[@]} -eq 0 ]; then
  echo "verify: no checks detected. Add a 'verify' list to .eng-ai.json." >&2
  exit 1
fi

if [ -n "${VERIFY_LIST:-}" ]; then
  printf '%s\n' "${steps[@]}"
  exit 0
fi

failed=0
for cmd in "${steps[@]}"; do
  if out=$(bash -o pipefail -c "$cmd" 2>&1); then
    echo "ok    $cmd"
  else
    failed=$((failed + 1))
    echo "FAIL  $cmd"
    printf '%s\n' "$out" | tail -n 40
  fi
done

if [ "$failed" -eq 0 ]; then
  echo "verify: PASS - ${#steps[@]} steps"
else
  echo "verify: FAIL - ${#steps[@]} steps, $failed failed"
  exit 1
fi
