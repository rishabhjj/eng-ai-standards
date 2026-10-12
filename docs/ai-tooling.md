# AI tooling around the kit

The kit itself ships two plugins (`guard`, `workflow`). Everything else is optional and sorted by who should use it. Every extra skill or MCP server costs context in every session, so the caps matter more than the list.

**Caps for tier 1:** about 15 to 20 skills, at most 3 MCP servers, at most one small session-start injector. Check a plugin's cost before adopting it: `claude plugin details <name>` prints its projected always-on tokens.

Install commands below come from each project's own documentation or from our research and have not all been run by us. Read a skill before installing it: skills can run commands.

## Tier 1: recommended for everyone

| Tool | Why | Install |
|---|---|---|
| `security-guidance` | on-edit security warnings (official) | `claude plugin install security-guidance@claude-plugins-official` |
| `kotlin-lsp`, `typescript-lsp`, `pyright-lsp`, `jdtls-lsp` | code intelligence; install the ones for your languages | `claude plugin install <name>@claude-plugins-official` |
| Trail of Bits plugins | static analysis, differential security review, insecure defaults, sharp edges, supply-chain audit | commands in `vendor.lock.json` under `installed`; see [THIRD_PARTY.md](../THIRD_PARTY.md) |
| `ponytail` | anti-bloat reflex, matches the ladder in `AGENTS.md` | `claude plugin marketplace add DietrichGebert/ponytail` |
| MCP: GitHub, Context7, one tracker | read-only by default | each server's own docs; three at most |

Trail of Bits notes: `static-analysis` can clone third-party Semgrep rulesets by URL, so keep its `third_party` list empty unless reviewed. `fp-check` is deliberately left out of tier 1: it registers a `Stop` hook with matcher `*` that runs an LLM prompt, so it fires at the end of every session.

## Tier 2: approved per repo or role

| Tool | Use it for | Notes |
|---|---|---|
| taste-skill | frontend repos (Next.js, Vite) that should not look generic | MIT; enable only in frontend repos |
| firecrawl | researching library docs and the web | needs an API key unless self-hosted; core is AGPL-3.0, get a license check; keep the key out of the repo |

## Tier 3: personal opt-in, not installed by the kit

| Tool | What it is | Risk |
|---|---|---|
| claude-mem | cross-session memory (local SQLite plus vector store, 5 lifecycle hooks) | optional cloud sync and hosted observer send data to third parties; set `CLAUDE_MEM_ONLINE_OPTIN=false` and use `<private>` tags; every hook adds overhead |
| humanizer | rewrites text to remove AI-writing tells | docs and PR text only; no effect on code quality |
| gstack | 23 roles and 8 power tools, Claude-first | heavy: registers hooks, needs Bun; overlaps the kit's workflow |
| caveman | terse-output mode | personal taste; injects text every session |

## Not used, on purpose

- Superpowers: its roles are covered by the vendored workflow, the `verify.sh` gate and native worktrees, and its always-on bootstrap costs tokens in every session.
- Marketing, video and writing-style skill packs: not engineering.
- The official `code-review` plugin and mattpocock's `code-review`: our `review` skill owns review, one owner per stage.
- `second-opinion`, `github-triage`, `git-cleanup` (Trail of Bits): external data flow or write and delete power; revisit with a specific need.

## Where each thing is installed

User level (every project): `guard`, the LSPs, `security-guidance`. Project level (only that repo): `workflow` and anything repo-specific. Personal tools stay at user level and out of shared settings.
