# Third-party skills

Pinned in `vendor.lock.json`. `python3 scripts/vendor.py verify` checks the vendored files offline; `check` reports upstream changes; `update` re-copies and re-applies our patches. Upstream changes arrive as a reviewed PR, never automatically: skills can run commands, so a human reads the diff first.

## Vendored (copied into `.agents/skills/`)

**mattpocock/skills**: https://github.com/mattpocock/skills, MIT, copyright Matt Pocock. License copy: `third_party/mattpocock-skills/LICENSE`.
Pinned in `vendor.lock.json`.

| Skill | Role |
|---|---|
| `grill-with-docs`, `grilling`, `domain-modeling` | clarify a plan, keep `GLOSSARY.md` and `docs/adr/` current |
| `to-spec`, `to-tickets`, `setup-matt-pocock-skills` | spec and tickets in the issue tracker (`gh issue ...`); the first two publish only after the user says yes, setup is user-invoked |
| `tdd`, `codebase-design` | the single TDD policy and its design vocabulary |
| `diagnosing-bugs` | disciplined bug diagnosis loop |
| `retro` | turn session mistakes into checks and rules |
| `writing-for-agents` | how to write skills and `AGENTS.md` |

Local patches (re-applied by `update`, listed in the lock; after editing one run `python3 scripts/vendor.py relock`): `tdd` points at our `review` skill instead of `code-review`; `retro` points at `standards/rules/` instead of `CODING_STANDARDS.md`; `grill-with-docs`, `retro`, `to-spec` and `to-tickets` are model-invocable with trigger phrases in their descriptions, and `to-spec` asks before publishing.

Not vendored on purpose: `code-review`, `implement`, `implement-spec`, `pr` (our `review` skill owns review; one owner per stage), `wayfinder`, `triage`, `ask-matt` and the rest.

## Installed from upstream (not copied)

**trailofbits/skills**: https://github.com/trailofbits/skills, license CC BY-SA 4.0 (ShareAlike, so copies would inherit it).
Reviewed at the commit in `vendor.lock.json`. Plugins: `static-analysis`, `differential-review`, `insecure-defaults`, `sharp-edges`, `supply-chain-risk-auditor`. Install commands are in the lock.

Not recommended by default: `fp-check` registers a `Stop` hook with matcher `*` that runs an LLM prompt, so it would fire at the end of every session once enabled. Enable it per repo if wanted. `static-analysis` can clone third-party Semgrep rulesets by URL; keep its `third_party` list empty unless reviewed.

## Updating from upstream

Manual on purpose: a skill can run commands, so an upstream change is reviewed by a person before it ships.

1. Detect: the weekly `vendor-check` workflow fails when upstream changed something listed here, or run `python3 -I scripts/vendor.py check` (prints the diff stat since the pinned commit).
2. Read the upstream diff on GitHub. Look for new shell commands, URLs and tool instructions.
3. On a branch, `python3 -I scripts/vendor.py update` (add `--name mattpocock-skills` for one source, `--source DIR` for a local clone at a chosen commit). It re-copies the skills, re-applies the patches in the lock, refreshes the hashes and the commit, and refuses symlinks. If a patch no longer applies it stops and names it: fix the `old` text in the lock, run `update` again.
4. `scripts/verify.sh`, open a PR with the diff, bump `VERSION` and the plugin versions, tag. Teammates receive it on `claude plugin update`.

Installed plugins (Trail of Bits) are not copied: each person runs `claude plugin update <name>@trailofbits`; after review, record the new commit under `installed` in the lock so `check` compares against it. The kit's own skills (`review`, `review-spec`, `review-postmortem`) are edited like any other code.

