#!/usr/bin/env bash
# PreToolUse(Edit|Write): SEC-002 secrets, keys, lockfiles, .git and the guard config are not hand-edited.
# Works for Claude Code (file_path) and Codex (apply_patch headers) via tool_paths.py.
# Checks the given path and its symlink-resolved destination. Fails closed if the helper cannot run.
here=${0%/*}; [ "$here" = "$0" ] && here=.
paths=$(python3 -I "$here/tool_paths.py" --resolve 2>&1)
rc=$?
if [ $rc -ne 0 ]; then
  echo "BLOCKED: guard hook could not run (rc=$rc): $paths" >&2
  exit 2
fi
while IFS= read -r f; do
  [ -n "$f" ] || continue
  case "$f" in /*) ;; *) f="/${f#./}" ;; esac
  case "$f" in
    *.env.example|*.env.sample) ;;
    */.eng-ai.json|*/.githooks/*|*/.claude/hooks/*|*/.claude/settings.json|*/.claude/settings.local.json|*/.codex/*hooks*)
      echo "BLOCKED [SEC-002]: $f configures the guard/hooks; ask the user to change it." >&2; exit 2 ;;
    */.env|*/.env.*|*.env|*.pem|*.key|*id_rsa*|*id_ed25519*|*id_ecdsa*|*.p12|*.keystore|*.jks|*/.git/*)
      echo "BLOCKED [SEC-002]: $f is secret/VCS material. Ask the user." >&2; exit 2 ;;
    *package-lock.json|*pnpm-lock.yaml|*yarn.lock|*poetry.lock|*uv.lock|*gradle.lockfile|*Cargo.lock|*Gemfile.lock|*go.sum|*composer.lock|*flake.lock|*Package.resolved)
      echo "BLOCKED [SEC-002]: $f is generated. Run the package manager instead of editing it." >&2; exit 2 ;;
  esac
done <<<"$paths"
exit 0
