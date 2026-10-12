# Standards

One file per rule in `rules/`, named `<ID>-<slug>.md`.

```markdown
---
id: SEC-001                 # ABC-123, unique, matches the filename
title: short imperative rule
status: approved            # approved = reported, never blocks | enforced = blocks
severity: critical          # critical | high | medium | low
check: hook:.githooks/pre-commit
---
Why the rule exists (required, one or two sentences).
```

## Every rule names its check
| check | target | must exist | must cite the ID |
|---|---|---|---|
| `hook:<path>` | git hook or Claude hook script | yes | yes |
| `review:<lens>` | `.agents/skills/review/lenses/<lens>.md` | yes | yes |
| `semgrep:<path>` | semgrep rule file | yes | yes |
| `ci:<path>` | CI workflow file | yes | yes |
| `linter:<tool>:<rule>` | a file under `lint-packs/` that configures the rule | yes | yes |

A rule whose check does not exist, or never mentions the rule ID, fails `scripts/standards-check.py`. An `enforced` rule cannot rely on a review lens alone, because review findings are judgment and do not block.

## Lifecycle
1. New rules land as `approved`: violations are reported, nothing blocks.
2. Promote to `enforced` in a PR once the check is deterministic and violation counts on the pilot repos are near zero.
3. Repos may tighten any rule. Loosening a security rule needs a documented exception with owner and expiry.

## Index
`AGENTS.md` carries a generated index between `<!-- standards:start -->` and `<!-- standards:end -->`. After adding or changing a rule run:

```bash
python3 scripts/standards-check.py --write-index
```
