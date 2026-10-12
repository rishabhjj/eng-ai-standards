#!/usr/bin/env bash
# PreToolUse(Bash): exit 2 blocks the call and feeds stderr back to the model.
# Rules enforced here: GIT-002 GIT-003 GIT-004 GIT-005 SEC-007 (parsing in guard_bash.py).
# Safety net only: gitconfig aliases, scripts and other binaries that call git are not followed.
# Fails closed: if the helper cannot run, the call is blocked instead of silently allowed.
here=${0%/*}; [ "$here" = "$0" ] && here=.
out=$(python3 -I "$here/guard_bash.py" 2>&1)
rc=$?
if [ $rc -eq 2 ]; then
  echo "BLOCKED by guard-bash [${out%%:*}]: ${out#*: }. Ask the user if this is really intended." >&2
  exit 2
fi
if [ $rc -ne 0 ]; then
  echo "BLOCKED: guard hook could not run (rc=$rc): $out" >&2
  exit 2
fi
exit 0
