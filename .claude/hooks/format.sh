#!/usr/bin/env bash
# PostToolUse(Edit|Write): fail-soft formatter. Only formats where the repo has opted in
# with its own config, so installing the guard plugin never reformats an unconfigured repo.
# Works for Claude Code (file_path) and Codex (apply_patch headers) via tool_paths.py.
root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
have() { command -v "$1" >/dev/null 2>&1; }
has_config() { for c in "$@"; do ls "$root"/$c >/dev/null 2>&1 && return 0; done; return 1; }

format_one() {
  f="$1"
  case "$f" in /*) ;; *) f="$root/$f" ;; esac
  [ -f "$f" ] || return 0
  case "$f" in
    *.py)
      if have ruff && { has_config ruff.toml .ruff.toml || grep -qs '^\[tool\.ruff' "$root/pyproject.toml"; }; then
        ruff format -q "$f" >/dev/null 2>&1
      fi ;;
    *.kt|*.kts)
      have ktlint && has_config .editorconfig && ktlint -F "$f" >/dev/null 2>&1 ;;
    *.ts|*.tsx|*.js|*.jsx|*.mjs|*.json|*.css)
      if has_config biome.json biome.jsonc; then
        (cd "$root" && npx --no-install biome format --write "$f") >/dev/null 2>&1
      elif has_config '.prettierrc*' 'prettier.config.*'; then
        (cd "$root" && npx --no-install prettier --write "$f") >/dev/null 2>&1
      fi ;;
  esac
}

paths=$(python3 -I "$(dirname "$0")/tool_paths.py" 2>/dev/null)
while IFS= read -r p; do
  [ -n "$p" ] && format_one "$p"
done <<<"$paths"
exit 0
