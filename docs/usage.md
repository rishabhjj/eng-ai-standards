# Using the kit day to day

After [setup](setup.md), nothing is manual per task. This page says what runs when, what the agent decides on its own, and how to adjust a rule for one repo.

## What runs when

| | Runs | Guaranteed? |
|---|---|---|
| Rules and working rules (`AGENTS.md`) | loaded into every session, Claude Code, Codex and Cursor | the agent reads them; following them is judgment |
| Guard hooks (force push, `--no-verify`, `.env` and lockfile edits, `curl \| sh`, bulk staging) | every agent command and edit, Claude Code and Codex | yes, the agent cannot skip a hook |
| Missing-tool warning | every session start | yes |
| Secret scan, commit-message format | every `git commit`, any tool or human | yes, in clones with `core.hooksPath` set |
| Lint, types, tests, build (`verify.sh`) | every `git push`, and the agent is told to run it before saying done | yes at push |
| CI scanners (gitleaks, actionlint block; osv, semgrep, zizmor, Trivy report) | every PR | yes, in repos that committed the workflow |
| `enforced` rules | hooks and CI block | yes |
| `approved` rules | linters and semgrep report; the review skill flags | reported, not blocked, until promoted |

Two layers, then: **guidance** (the rules file and the skills, which the agent applies with judgment) and **enforcement** (hooks and CI, which run whatever the agent does). A rule only becomes a guarantee when it has a deterministic check and is promoted to `enforced`.

## What the agent does on its own

Skills carry a one-line description that is always visible; the agent loads a skill when the task matches it. In Codex they appear as `workflow:<name>`.

| You say | The agent |
|---|---|
| "plan feature X", "design this", a change touching more than 3 files | drafts a plan (working rule 2), may run `grill-with-docs` to sharpen it, runs `review-spec` on the plan, then **offers** `to-spec` and `to-tickets`. Nothing is published to the tracker without your yes. |
| "review this plan / spec / design" | `review-spec` |
| "review", "check this before I open a PR" | `review`: correctness, security, tests, simplicity and data lenses; every finding needs a concrete failing input; findings are advisory and never block |
| "fix this bug", "it is failing" | `diagnosing-bugs`, then `tdd` for the fix |
| "add feature", "implement" | `tdd` and `codebase-design` |
| shares an incident write-up | `review-postmortem` |
| "retro" | `retro`: turns the session's mistakes into proposed rules and checks |

Only `setup-matt-pocock-skills` (one-time tracker configuration) must be typed by you. You can force any skill with `/name`.

The agent choosing a skill is still judgment: it usually triggers, not always. The checks that must always happen are hooks, not skills.

## Configuration: `.eng-ai.json`

Plain JSON, validated by the installer (unknown keys and wrong types fail):

```json
{
  "verify": ["npm run lint", "npm test"],
  "enforce": ["semgrep"],
  "disabled": ["COD-004"],
  "exceptions": [
    {"rule": "SEC-003", "owner": "@alice", "expires": "2026-12-31", "reason": "legacy admin API, ticket ENG-12"}
  ]
}
```

| Key | Effect |
|---|---|
| `verify` | the commands `verify.sh` runs instead of auto-detection (required for monorepos) |
| `enforce` | CI checks that block instead of report: any of `semgrep`, `osv`, `zizmor`, `trivy` |
| `disabled` | turns a non-security rule off for this repo: it leaves the `AGENTS.md` index (listed as disabled), the guard and commit-msg hooks skip it, and its semgrep file is removed on `update --apply`. Linter settings stay in the base packs; override them in your own config, which extends them. |
| `exceptions` | a tolerated violation of any rule with an owner, an ISO expiry date and a reason. Shown to the agents in `AGENTS.md`; every check stays on; `doctor` fails once it expires. |
| `languages` | override language detection, for example `["python"]` in a repo whose TypeScript is only tooling |
| `kit_version`, `managed`, `marketplace` | written by the installer; do not edit |

**Security rules (`SEC-*`) cannot be disabled.** `doctor` fails if you try. Use `exceptions`.

Skills are switched off per plugin, not per rule: set `"workflow@eng-ai-standards": false` under `enabledPlugins` in `.claude/settings.json` and keep `guard`.

## Layering with what the repo already has

| Your repo has | What happens |
|---|---|
| `AGENTS.md` with your own rules | kept; the kit block is appended between markers. Your rules can tighten anything; loosening a security rule needs an exception. |
| `CLAUDE.md` | never edited; it needs `@AGENTS.md` on its first line, or Claude ignores the kit block. Claude-only notes go below the import. |
| `.agents/skills/` of your own | untouched; the kit's skills come from the plugin and are namespaced, so names do not clash. If one of yours covers the same stage as a kit skill (your own TDD or review), disable the `workflow` plugin for that repo and keep `guard`; one owner per stage. |
| `.githooks/` or husky | not overwritten; you call the kit hooks from yours. `doctor` accepts a husky hook that delegates to `.githooks/`. |
| `.claude/settings.json` with hooks and permissions | merged add-only; your hooks keep running next to the guard. Any hook that exits 2 blocks, so the guard cannot be overridden by a repo hook. |
| Linter configs | yours extend the base packs; your settings win. |

Nested `AGENTS.md` or `CLAUDE.md` files in subdirectories still work for service-specific rules in a monorepo.

## Promoting a rule

New rules land as `approved`: violations are reported, nothing blocks. After a few weeks on real repos, export PR data (`scripts/export-pr-data.py`, needs `gh`) and run `scripts/metrics.py`. Promote a rule to `enforced` in a PR when its check is deterministic (a hook, semgrep, a linter or CI, never a review lens alone) and violations are near zero. Details: [standards/README.md](../standards/README.md).
