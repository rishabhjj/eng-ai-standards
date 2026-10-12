# Publish checklist

Maintainer checklist. Done: owner (`@rishabhjj` in CODEOWNERS), MIT license, repo name. Open items need an account or a decision only the owner has.

## Decide
- [ ] **Three pilot repos:** one Kotlin, one TypeScript, one Python.

## Before the first push
- [ ] `scripts/verify.sh` passes.
- [ ] Read `git status` and `git diff` once. Nothing in this repo should be a secret: `gitleaks detect --no-git --source .` is clean.
- [ ] Commit in small conventional commits (`type(scope): subject`), staging explicit paths.

## Repository settings
- [ ] Protect `main`: require a pull request and the `standards` check, require CODEOWNERS review, block force pushes.
- [ ] Require review for the paths in `CODEOWNERS` (branch protection: "Require review from Code Owners").
- [ ] Turn on Dependabot or Renovate (config is in `renovate.json`); enable secret scanning and push protection.
- [ ] Actions permissions: read-only by default.

## First real install (what is still unproven)
- [ ] On a second machine, `claude plugin marketplace add rishabhjj/eng-ai-standards`, install `guard` and `workflow`, run `claude plugin details workflow` and compare the token cost with `docs/setup.md`.
- [ ] Same in Codex: `codex plugin marketplace add rishabhjj/eng-ai-standards`, add both plugins, approve the hooks with `/hooks`, then try a force push and an edit to `.env` and confirm they are blocked.
- [ ] On a pilot repo: `python3 ~/.eng-ai-standards/installer/eng_ai.py bootstrap --apply --marketplace rishabhjj/eng-ai-standards`, open the repo in Claude, confirm it offers the plugins.
- [ ] Log in (`claude /login`) and run `scripts/run-evals.sh --runs 1 --ablation none` once.

## Release
- [ ] README "Develop the kit", Releases: bump, tag, changelog line.

## After a few weeks on the pilot repos
- [ ] Export PR data and run `scripts/metrics.py` (see `scripts/export-pr-data.py`; it needs the GitHub CLI).
- [ ] Promote a rule from `approved` to `enforced` only when its check is deterministic and violations on the pilots are near zero.
- [ ] Disable any review lens whose precision is below the bar.
