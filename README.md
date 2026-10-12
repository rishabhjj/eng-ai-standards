# eng-ai-standards

One shared engineering setup for AI coding assistants (Claude Code, Codex, Cursor), for any repo in Kotlin, Java, TypeScript or Python. Rules are enforced by tools (linters, git hooks, CI); the model only judges what tools cannot.

**Status: v0.1, not yet piloted.** See [what is verified](docs/setup.md#verified-so-far) and what is not.

## Use it

Full walkthrough with checks at each step: [docs/setup.md](docs/setup.md). What runs when, and how to adjust a rule per repo: [docs/usage.md](docs/usage.md). The short version:

**Once per person:** install `gitleaks` (required) and `semgrep`, then the `guard` and `workflow` plugins for your assistant. Codex and Cursor users also clone the kit at a release tag (the installer lives in it; Claude Code gets it through the plugin).

```bash
brew install gitleaks semgrep && claude plugin marketplace add rishabhjj/eng-ai-standards && claude plugin install guard@eng-ai-standards && claude plugin install workflow@eng-ai-standards
```

**Once per repo**, in a project whose build already exists: in Claude Code type `/setup-repo` (dry run, apply on your yes, doctor); or by hand `python3 ~/.eng-ai-standards/installer/eng_ai.py bootstrap --apply --marketplace rishabhjj/eng-ai-standards`. Fix every `FAIL` from `doctor`, then commit.

**Each teammate, once per clone:** `git config core.hooksPath .githooks`.

`bootstrap` never overwrites a file the repo changed, never edits an existing `CLAUDE.md` or git hook (it tells you what to merge by hand and exits 1), and records what it installed in `.eng-ai.json`. `update`, `doctor` and `uninstall` work the same way.

## What a repo gets

| Piece | What it does |
|---|---|
| `AGENTS.md` managed block | working rules, anti-bloat ladder, the standards index; your own text stays outside the block |
| `scripts/verify.sh` | one command for lint, types, tests and build; detects Gradle, Maven, npm/pnpm/yarn (`lint`, `typecheck`, `test`, `build`), Python (ruff, mypy, pytest or unittest); a monorepo must list its steps under `verify` in `.eng-ai.json` |
| Git hooks | secret scan (gitleaks), conventional commits, `verify.sh` before push |
| CI workflow | gitleaks, actionlint block; osv-scanner, semgrep, zizmor, Trivy start report-only (add to the `enforce` list in `.eng-ai.json` to block) |
| `.eng-ai/lint/` | base lint configs and semgrep rules for the repo's languages; the repo extends them |
| PR template | evidence, new-dependency justification, merge risk, agent-authored box |
| Plugins | `guard` (hooks) and `workflow` (skills), enabled for the project |

## How it fits together

- **[standards/](standards/README.md):** one file per rule. Each names a check that exists and cites the rule ID, or `scripts/standards-check.py` fails. New rules start `approved` (reported) and become `enforced` (blocking) in a PR.
- **[lint-packs/](lint-packs/README.md):** configs and semgrep rules that back the rules.
- **[Review skill](.agents/skills/review/SKILL.md):** correctness, security, tests, simplicity and data lenses; findings need a concrete failing input. Observe-only: findings are advisory.
- **Third-party skills:** [THIRD_PARTY.md](THIRD_PARTY.md). Pinned in `vendor.lock.json`; upstream changes arrive as a reviewed PR.
- **Planning and incident reviewers:** `review-spec` runs on any plan or design (and automatically after the AI drafts a plan for a bigger change); `review-postmortem` on incident write-ups. `to-spec` and `to-tickets` publish to the tracker only after you say yes. Only `setup-matt-pocock-skills` (one-time tracker setup) is user-invoked.
- **Evals:** [evals/README.md](evals/README.md), run with `scripts/run-evals.sh`. **Metrics:** `scripts/export-pr-data.py` then `scripts/metrics.py` (monthly, manual).
- **Why it is built this way, and what is not covered:** [docs/design.md](docs/design.md).
- **Docs:** [setup](docs/setup.md), [usage](docs/usage.md), [optional tools](docs/ai-tooling.md), [sandbox](docs/sandbox.md), [maintainer checklist](docs/publish.md).

## Configuration and layering

`.eng-ai.json` holds the repo's `verify` commands, which CI checks block (`enforce`), non-security rules switched off (`disabled`) and tolerated violations with an owner and expiry (`exceptions`). Security rules cannot be disabled. A repo can tighten any rule; its own `AGENTS.md` text, skills, hooks and lint configs stay in place next to the kit's. Details: [docs/usage.md](docs/usage.md).

## Develop the kit

```bash
git config core.hooksPath .githooks
scripts/verify.sh        # tests, standards check, vendor lock, semgrep fixtures, plugin manifest
```

Add a rule: create `standards/rules/ABC-123-slug.md`, point `check:` at something that exists and cites the ID, then `python3 scripts/standards-check.py --write-index`. Change a skill or rule only with a before/after result from the evals once they exist.

Releases: bump `VERSION` and the plugin versions in `.claude-plugin/marketplace.json` together (a test enforces it). Teammates only receive changes on a version bump.

## License

MIT, see [LICENSE](LICENSE). Vendored third-party skills keep their own licenses: [THIRD_PARTY.md](THIRD_PARTY.md).
