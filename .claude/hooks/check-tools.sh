#!/usr/bin/env bash
# SessionStart: tell the user (and the model, via stdout) when a required tool is missing.
# Rules: SEC-001 needs gitleaks. Fail-soft: never blocks the session.
if ! command -v gitleaks >/dev/null 2>&1; then
  msg="eng-ai: gitleaks is not installed, so commits are blocked (SEC-001). Tell the user to run: brew install gitleaks (other OS: https://github.com/gitleaks/gitleaks#installing). Do not run git commit until it is installed."
  echo "$msg"
  echo "$msg" >&2
fi
exit 0
