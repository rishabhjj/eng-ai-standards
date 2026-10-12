# Design

Why the kit is shaped this way, what is built, and what is not. Keep it current: delete a decision when it stops being true instead of annotating it.

## Goal

One shared engineering setup for AI coding assistants (Claude Code, Codex, Cursor) across Kotlin, Java, TypeScript (Nest, Next, Vite) and Python, for a small team on per-seat plans. Every repo can add its own rules on top.

## Principles

1. **Deterministic tools enforce, the model judges.** Linters, types, tests, scanners, git hooks and CI do the blocking. The model reviews only what tools cannot check.
2. **The repo is the source of truth.** Rules that must always apply live in repo files, git hooks and CI, because a laptop-only install does not reach new clones or cloud tasks.
3. **One owner per workflow stage.** No two skills or reviewers do the same job.
4. **Progressive disclosure.** A small always-loaded core; everything else loads on demand. Measured: `guard` about 0 tokens, `workflow` about 620.
5. **Apply the anti-bloat ladder to the kit itself:** needs to exist, already here, stdlib, platform-native, installed dependency, then new code.
6. **Small-team scale.** No gateway, org control plane or background agents until a measured need.

## Layers

| Layer | What | Where |
|---|---|---|
| Instructions | `AGENTS.md` (at most 100 lines) with a generated rules index; `CLAUDE.md` is one import line | per repo, from `bootstrap` |
| Standards | one file per rule, each naming a check that exists | `standards/` |
| Deterministic gates | `verify.sh`, lint packs, semgrep rules, git hooks, CI scanners | `scripts/`, `lint-packs/`, `.githooks/`, `.github/` |
| Agent guardrails | Claude and Codex hooks for dangerous commands and secret edits; sandbox guidance | `.claude/hooks/`, `docs/sandbox.md` |
| Review | one `review` skill, 5 lenses, a judge step; optional spec and postmortem reviewers | `.agents/skills/` |
| Skills and plugins | vendored workflow skills, installed Trail of Bits plugins, two marketplace plugins | `vendor.lock.json`, `.claude-plugin/` |
| Feedback | evals with a no-plugin baseline, a weekly retro, monthly metrics | `evals/`, `scripts/metrics.py` |
| Distribution | installer (`bootstrap`, `update`, `doctor`, `install-skills`), a versioned marketplace | `installer/` |

## Decisions and why

| Decision | Why | Evidence |
|---|---|---|
| `AGENTS.md` is the shared file; `CLAUDE.md` only imports it | Claude reads `AGENTS.md` only when no `CLAUDE.md` exists; Codex and Cursor read it natively | Claude memory docs (primary) |
| Keep `AGENTS.md` short, put must-follow rules in an index | long context files can hurt, and skills are not always invoked | OpenAI harness article (via a summary), Vercel and ETH evals (via a summary) |
| Every rule names a check, with `approved` then `enforced` | rules nothing checks do not get followed; new rules must not block everyone on day one | Cloudflare engineering standards (primary) |
| Linters and tests first, then specialists, then a judge; findings need a concrete failing input | one big prompt floods with false positives; precision decides whether people keep using it | Cloudflare AI review (primary), Uber and cubic (summaries) |
| Review runs locally in v1 | CI-hosted review needs an API key and per-seat plans have none | our situation |
| No gateway, managed settings or spend caps | they solve shared-billing and thousands-of-users problems we do not have | Cloudflare stack (primary), judgement |
| One mattpocock-based workflow; Superpowers dropped | the two overlap on TDD, planning and review, and Superpowers' always-on bootstrap costs tokens every session | repo and docs comparison |
| mattpocock skills vendored and pinned; Trail of Bits installed from upstream | MIT lets us copy and patch; Trail of Bits is CC BY-SA 4.0 and script-heavy | licenses read in each repo |
| Upstream skill changes arrive as a reviewed PR | skills can run commands, so an update is a supply-chain event | `scripts/vendor.py`, weekly check |
| `fp-check` is not in tier 1 | it registers a `Stop` hook with matcher `*` that runs an LLM prompt in every session | its `hooks.json` |
| Plugin split: `guard` (hooks) and `workflow` (skills) | hooks are near-free at user level; skills are best enabled per project | `claude plugin details` |
| Codex uses the same `.claude-plugin` marketplace | Codex 0.162 accepts it and generates its own manifest | tested locally |
| Skills live only in `.agents/skills/` | Codex and Cursor read it; no second copy to keep in sync | design choice |
| Sandbox guidance, not a copied devcontainer | Anthropic's reference is "all rights reserved"; its firewall also leaves DNS and SSH open | license and script read |
| Cursor gets `install-skills`, not a plugin | its plugin system needs a Teams or Enterprise dashboard and is unverified | Cursor docs |
| Evals use `claude plugin eval` with a baseline arm | gives a before and after number for any change to `AGENTS.md`, skills or rules | Claude eval docs |

## Status

**Built and tested:** standards and validator, git hooks, lint packs and semgrep rules (checked against the real tools, except Java), `verify.sh`, installer, CI workflows, review skill and lenses, vendored skills, marketplace, guard hooks for Claude and Codex payloads, evals structure, metrics logic, docs.

**Built, not yet exercised:** the eval cases against the model (needs a logged-in CLI), the PR exporter (needs `gh`), project auto-onboarding in Claude, Codex hooks in a live session, installs from a real GitHub source.

**Phases**

| Phase | State |
|---|---|
| 0 Verify tools and formats | done for Claude and Codex with local sources; Cursor not verified |
| 1 Kit, standards v1 (non-blocking), installer, vendored skills | built |
| 2 Review in observe-only mode, evals, metrics | built, waiting for the pilot repos |
| 3 Promote the first rules to `enforced` | needs pilot data |
| 4 Only if a need is measured | CI-hosted review, rule tooling, dashboards, gateway, background agents |

## Not covered

DAST and runtime security, IaC depth, privacy and SOC 2 evidence, performance testing, accessibility gates, deeper observability (tracing, SLOs), migration-lock analysis, release engineering, CI-hosted review, an org gateway, background agents.

## Success measures (thresholds are placeholders until measured)

New engineer productive in under 30 minutes; review precision above a bar per lens (set after about 3 weeks); always-loaded tokens under a calibrated budget; agent-PR rework rate trending down; zero secret leaks.

## Known risks

Review precision is unproven (hence observe-only). Eval scores vary between runs, so compare means. Legacy repos need linter baselines (mypy is the hardest). `verify.sh` detection is fragile in monorepos (override with the `verify` list in `.eng-ai.json`). Guard hooks parse commands but cannot follow aliases or scripts, so they are a safety net and CI is the gate. A public repo is a supply-chain target: pin to tags, protect `main`, require review on hooks, installer and vendored skills.

## Sources

Primary: Cloudflare ([internal AI stack](https://blog.cloudflare.com/internal-ai-engineering-stack/), [AI code review](https://blog.cloudflare.com/ai-code-review/), [standards enforcement](https://blog.cloudflare.com/engineering-standards-enforcement/)); Stripe [Minions part 1](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents); Spotify [Honk part 1](https://engineering.atspotify.com/2025/11/spotifys-background-coding-agent-part-1); Claude Code docs for [memory](https://code.claude.com/docs/en/memory), [plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) and [plugin evals](https://code.claude.com/docs/en/plugin-evals.md); Codex [hooks](https://learn.chatgpt.com/docs/hooks) and [skills](https://learn.chatgpt.com/docs/build-skills); [Cursor docs](https://cursor.com/docs/plugins).

Secondary, used with care: OpenAI's harness engineering article through a [ZenML summary](https://www.zenml.io/llmops-database/harness-engineering-structuring-context-and-guardrails-for-ai-coding-agents-in-production); Uber, Datadog and cubic through search summaries; the Vercel and ETH Zurich AGENTS.md evaluations through a blog summary.
