#!/usr/bin/env bash
# Validate the Claude marketplace manifest with the real CLI. Skips (loudly) when claude is absent.
cd "$(git rev-parse --show-toplevel)" || exit 1
command -v claude >/dev/null 2>&1 || { echo "validate-plugin: SKIPPED (claude CLI not found)"; exit 0; }
claude plugin validate . --strict
