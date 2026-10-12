# Evals

Cases for `claude plugin eval`, which runs each case several times with the kit's skills loaded and, by default, again without them, and reports both scores and the difference. This is how a change to `AGENTS.md`, a skill or a rule earns its place: no such change merges without a before and after number.

**Status: the cases and fixtures are verified, the model behaviour is not.** The harness resolves the plugin and runs the scaffolds, but a run needs a logged-in `claude` CLI and nobody has run the suite with credentials yet.

## Run

```bash
claude /login                               # once, in a terminal: eval child sessions need their own login
scripts/run-evals.sh --runs 1 --ablation none     # cheap smoke run, one arm
scripts/run-evals.sh                              # full: 3 runs per case, with and without the plugin
scripts/run-evals.sh --case 'review-*' --threshold 0.8
```

`run-evals.sh` assembles a throwaway plugin in `build/eval-plugin` (the repo root is a marketplace, not a plugin), so skills and cases are copied there. It caps spend at `EVAL_MAX_COST_USD` (default 5). Cost is roughly cases x runs x 2 arms agent runs, plus short judge calls. Results land in `build/eval-plugin/evals/results/`.

Cases run Bash-free on purpose: some machines cannot run Bash-granting evals (for example a symlink inside `~/.docker`), and a Bash-free suite runs everywhere. Review cases therefore receive the diff as `changes.diff`.

## Cases

| Case | Checks |
|---|---|
| `review-catches-sql-injection` | the review flags the f-string query, cites `db.py:<line>`, and the `review` skill fired |
| `review-clean-diff` | a safe refactor gets no invented security finding and no blockers |
| `review-catches-swallowed-error` | the `except Exception: pass` is flagged, and missing tests are noted |
| `tdd-bugfix` | a test file is written before `calc.py` is edited, the fix is percentage based, and `tdd` fired |

Every case has at least one deterministic grader (regex, file or tool check); model-judged graders are used only for the "no blockers" judgement, where a regex cannot decide.

## Reading results

- **WITH vs W/OUT and the delta:** the delta is what the kit contributed. A case that scores 1.0 both ways means the kit did not make it pass.
- Graders that check "the skill fired" are excluded from the score in a two-arm run, so they do not inflate the delta.
- If a skill-fired grader passes but the delta is negative, suspect the judge or the rubric before the skill; rerun with `--judge-model sonnet`.

## Adding a case

1. Make `evals/<name>/` with `prompt.md`, `case.yaml` (copy an existing one), a `scaffold.sh` that builds the workspace, and `graders/*.md`.
2. Prove the fixture: the bug must reproduce, and the clean diff must keep its tests green. `scripts/tests/test_evals.py` has the pattern.
3. Prefer a regex, `file_exists` or `tool_used` grader. Add a replay case whenever a real bad PR slips through review.

## When to run

Before merging a change to `AGENTS.md`, a skill, a lens or a rule. Judge scores vary between runs, so compare means over 3 runs, not single runs.
