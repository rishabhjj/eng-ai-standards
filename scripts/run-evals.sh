#!/usr/bin/env bash
# Run the eval suite against an assembled plugin, with a cost ceiling. Extra arguments go to
# `claude plugin eval`, for example: scripts/run-evals.sh --case 'review-*' --runs 1 --ablation none
# These runs call the model with your own credentials and count against your plan.
# Cases are Bash-free on purpose: some machines cannot run Bash-granting evals.
root="$(git rev-parse --show-toplevel)" || exit 1
command -v claude >/dev/null 2>&1 || { echo "run-evals: claude CLI not found" >&2; exit 1; }
python3 -I "$root/scripts/build-eval-plugin.py" "$root/build/eval-plugin" || exit 1
exec claude plugin eval "$root/build/eval-plugin" --scaffold \
  --max-cost-usd "${EVAL_MAX_COST_USD:-5}" "$@"
