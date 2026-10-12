# Setup

Two levels. **Machine level** is once per person and covers every repo they open. **Repo level** is once per repository, by one person, then committed so teammates get it from `git clone`. Each step says what you should see, so you know it worked.

Supported: macOS and Linux with bash, git and Python 3. Windows is not supported (the hooks are bash scripts); use WSL.

## Machine level (once per person)

### 1. Tools

```bash
brew install gitleaks semgrep
```

`gitleaks` is required: without it `git commit` is blocked and `doctor` fails. `semgrep` runs the same rules locally that CI runs. Other OS: [gitleaks](https://github.com/gitleaks/gitleaks#installing), [semgrep](https://semgrep.dev/docs/getting-started/quickstart). Also install your project's own linters (`ruff`, `mypy`, ESLint, detekt...); `verify.sh` runs whatever your project configures.

Check: `gitleaks version` prints a version.

### 2. The kit

The installer lives in the kit, not in your project. Clone it once, pinned to a release:

```bash
git clone --branch v0.1.0 https://github.com/rishabhjj/eng-ai-standards ~/.eng-ai-standards
```

Check: `python3 ~/.eng-ai-standards/installer/eng_ai.py doctor --target .` runs (it will say `.eng-ai.json missing` in a repo that is not set up yet; that is expected).

### 3. Plugins for your assistant

Two plugins. `guard` is hooks only: it blocks force pushes, `--no-verify`, `git reset --hard`, bulk staging, `curl | sh`, and hand-edits of `.env`, keys and lockfiles. `workflow` is the skills: `review`, `review-spec`, `tdd`, `diagnosing-bugs`, planning and ticket skills.

**Claude Code** (CLI or desktop app; in the app: **+** next to the prompt, Plugins, Add plugin):

```bash
claude plugin marketplace add rishabhjj/eng-ai-standards
```
```bash
claude plugin install guard@eng-ai-standards
```
```bash
claude plugin install workflow@eng-ai-standards
```

Check: `claude plugin details guard` lists its hooks. In a new session, asking Claude to run `git push --force` is refused with `BLOCKED by guard-bash [GIT-002]`.

**Codex** (CLI or ChatGPT desktop app):

```bash
codex plugin marketplace add rishabhjj/eng-ai-standards
```
```bash
codex plugin add guard@eng-ai-standards
```
```bash
codex plugin add workflow@eng-ai-standards
```

Then approve the hooks once with `/hooks`. Codex does not trust a plugin's hooks on install; trust is tied to a hash of the hook definition, so a release that changes a hook asks again. Codex reads the same `.claude-plugin/marketplace.json` and lists skills as `workflow:<name>`.

**Cursor**: no plugin support. Cursor reads `AGENTS.md` and `.agents/skills/` in each repo. Copy the kit's skills to the folder it reads for every project:

```bash
python3 ~/.eng-ai-standards/installer/eng_ai.py install-skills --apply
```

Add-only: it never overwrites a skill it did not install. Cursor gets no guard hooks; for Cursor the git hooks and CI are the enforcement.

## Repo level (once per repository, then commit)

Do this in a project that already has its build set up (a `package.json`, `pyproject.toml`, `gradlew` or `pom.xml` with lint and test commands). On an empty repo there is nothing to detect, and every push would be blocked until you add a `verify` list.

### 4. Preview, then apply

From the project root (or add `--target /path/to/project`):

```bash
python3 ~/.eng-ai-standards/installer/eng_ai.py bootstrap
```
```bash
python3 ~/.eng-ai-standards/installer/eng_ai.py bootstrap --apply --marketplace rishabhjj/eng-ai-standards
```

The first command is a dry run and writes nothing. The second adds: the `AGENTS.md` managed block (your own text stays outside it), a one-line `CLAUDE.md` that imports it, `scripts/verify.sh`, `.githooks/`, `.github/workflows/eng-ai-security.yml`, the PR template, `.eng-ai/lint/` for your languages, the plugin entries in `.claude/settings.json`, and `.eng-ai.json` recording what it installed. It sets `core.hooksPath` to `.githooks` for your clone.

Check: it prints `applied:` with a list, then `next: ... doctor`. **Exit code 1 means there is a `needs a human:` line.**

### 5. Handle every `needs a human:` line

It never overwrites your files. The common ones:

| Line | What to do |
|---|---|
| `CLAUDE.md exists and does not import AGENTS.md` | Add `@AGENTS.md` as its first line, or Claude will not see the rules. |
| `.githooks/pre-commit differs ... merge by hand` | Call the kit hook from your existing one, or move your logic into it. |
| `core.hooksPath is '.husky', not .githooks` | Add a line to each husky hook that runs the matching `.githooks/<hook>`. `doctor` accepts that. |
| `gitleaks is not on PATH` | Step 1. |
| `verify.sh detects no checks (or found nested projects)` | Step 7. |

### 6. Connect the lint packs

The base configs are in `.eng-ai/lint/`. Your own config extends them with one line per tool (table in [lint-packs/README.md](../lint-packs/README.md)), so your overrides win. Check: `doctor` says `<language> config extends the base lint pack`.

### 7. Check the verify steps

```bash
VERIFY_LIST=1 scripts/verify.sh
```

This prints the commands `verify.sh` detected. It runs on every `git push` and when the agent says it is done. If a step is missing or wrong, or you have a monorepo (it refuses to guess when it finds nested projects), list the commands yourself in `.eng-ai.json`:

```json
{ "verify": ["npm run lint", "npm test", "cd services/api && ruff check . && pytest -q"] }
```

Check: `scripts/verify.sh` ends with `verify: PASS`.

### 8. Health check

```bash
python3 ~/.eng-ai-standards/installer/eng_ai.py doctor
```

Fix every `FAIL`. `WARN` lines are advisory. Check: exit code 0.

### 9. Commit

Stage the added files by path (the guard blocks `git add -A`) and commit. Optional: run `/setup-matt-pocock-skills` once if you want `to-spec` and `to-tickets` to publish to your issue tracker; without it they write local files.

## Each teammate, once per clone

Git does not let a repo enable its own hooks, so after cloning:

```bash
git config core.hooksPath .githooks
```

Plus machine-level steps 1 to 3 if they are new. Claude Code offers the project's plugins automatically when they open the repo; Codex users run the three `codex plugin` commands and `/hooks` once.

## Upgrade

```bash
git -C ~/.eng-ai-standards fetch --tags && git -C ~/.eng-ai-standards checkout v0.2.0
```

Then in each project: `update --apply`, then `doctor`. `update` replaces only files you did not change and lists the rest. `doctor` warns when a project was set up with an older kit than the one on disk. Plugins: `claude plugin update guard@eng-ai-standards workflow@eng-ai-standards` or `codex plugin marketplace upgrade`.

## Uninstall

```bash
python3 ~/.eng-ai-standards/installer/eng_ai.py uninstall
```
```bash
python3 ~/.eng-ai-standards/installer/eng_ai.py uninstall --apply
```

Removes what `bootstrap` added and nothing else: managed files that you did not change, the `AGENTS.md` block, the one-line `CLAUDE.md`, the `core.hooksPath` setting, the plugin entries, `.eng-ai.json`. Files you changed are listed and left in place. Your own `AGENTS.md` text and your lint configs are untouched; remove the `extend` lines yourself. Plugins are per user: `claude plugin uninstall guard@eng-ai-standards workflow@eng-ai-standards`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `pre-commit: gitleaks is required (SEC-001)` | gitleaks not installed | step 1 |
| `commit-msg: subject must match 'type(scope): subject'` | GIT-001 | `feat(api): add retry`; `fixup!` and `squash!` are exempt |
| `verify: no checks detected` or `nested projects found` on push | nothing auto-detected, or a monorepo | step 7 |
| Push is slow | `verify.sh` runs everything | trim the `verify` list; per-package change detection is not built |
| Claude ignores the rules | `CLAUDE.md` without `@AGENTS.md`, or Claude Code older than 2.1.277 reading `AGENTS.md` directly | add the import line; `claude update` |
| `BLOCKED by guard-bash` on a command you meant | the hook is a safety net and may block text that only mentions a dangerous command | run it yourself in a terminal; see limits below |
| `BLOCKED: guard hook could not run` | python3 missing from the agent's PATH | the hooks fail closed on purpose; fix PATH |
| Codex hooks never fire | hooks not trusted | `/hooks` in Codex, approve |
| `doctor`: `FAIL  AGENTS.md has no managed block` | someone deleted the markers | `update --apply` re-adds it |
| `doctor`: `exception to SEC-xxx expired` | the exception in `.eng-ai.json` passed its date | renew with a new date and reason, or fix the code |
| Hooks did not run for a teammate | `core.hooksPath` is per clone | they run `git config core.hooksPath .githooks` |

## Limits of the guard hooks

The `guard` hooks are a safety net for agents, not a sandbox. They parse git's global options (`-C`, `-c`, `--config-env`, `--git-dir`), config passed through the environment (`GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_COUNT` with `GIT_CONFIG_KEY_n`, directly or via `env`), command-line aliases (`-c alias.x=...` is blocked outright), the long-option abbreviations git accepts (`--har`, `--forc`, `--no-ver`), short-flag clusters (`-Av`, `-xdf`, `-anm`), whole-tree pathspecs (`.`, `..`, `./.`, `:/`), `+refspec` force pushes, chained commands, `bash -c '...'` bodies, `$(...)` and backtick substitutions, line continuations, heredocs fed to a shell and `<(curl ...)` process substitution. Both hooks fail closed: if the helper cannot run, the call is blocked.

They do not follow aliases defined in gitconfig files, scripts, variables or other binaries that call git, and they may block a command that only prints a dangerous one (for example `echo git push -f`). The blocking gates are the git hooks and CI.

## Verified so far

| Claim | How |
|---|---|
| Claude installs both plugins from the marketplace; `guard` loads its hook events at about 0 tokens, `workflow` loads the skills at about 620 tokens | `claude plugin install` and `claude plugin details` in an isolated `CLAUDE_CONFIG_DIR` (measured with 2 hook events and 7 model-visible skills; now 4 events and 13 visible skills, not re-measured) |
| Codex 0.162.0 accepts the same marketplace, installs and enables both plugins, carries the skill paths and hooks into its generated manifest | `codex plugin marketplace add` and `codex plugin add` in an isolated `CODEX_HOME`, local directory source |
| Codex lists model-visible skills as `workflow:<name>` and hides user-only ones | `codex debug prompt-input` |
| Hook scripts work with Claude's `file_path` payload and Codex's `apply_patch` payload | unit tests with payloads built from the official hooks documentation |
| `bootstrap`, `update`, `doctor`, `uninstall` on empty repos, repos with existing `CLAUDE.md`/`AGENTS.md`/hooks, husky, monorepos | unit tests in `scripts/tests/test_installer.py` |

## Not verified

- Hooks running inside a live Codex session (needs a logged-in session; the `/hooks` trust step applies).
- The real shape of a Codex `apply_patch` payload: the tests follow the documentation, not an observed payload.
- Installing from a GitHub `OWNER/REPO` source: tested only with a local directory source.
- The `S113`, `T20` and `no-console` lint settings added in v0.1 against the real ruff and ESLint.
- Cursor.
