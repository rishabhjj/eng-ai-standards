---
name: setup-repo
description: Set this repository up with the eng-ai-standards kit, or update, check (doctor) or uninstall it, using the installer shipped inside the plugin. Use when the user asks to set up, install, apply, update, check or remove the kit, standards, hooks or guard in this repo. Always dry-runs and asks before applying.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/installer/eng_ai.py *), Bash(VERIFY_LIST=1 scripts/verify.sh)
---

# Set up this repo with the kit

The installer is `${CLAUDE_PLUGIN_ROOT}/installer/eng_ai.py`. If that path still contains the literal text `CLAUDE_PLUGIN_ROOT` (Codex and Cursor do not substitute it), use `~/.eng-ai-standards/installer/eng_ai.py` instead and tell the user it needs the kit cloned there (docs/setup.md step 2).

Pick the command from what the user asked: "check" or "doctor" → `doctor`, "update" → `update`, "remove" or "uninstall" → `uninstall`. Otherwise: `bootstrap` when there is no `.eng-ai.json` in the repo root, else `update`.

## Steps

1. Dry run first, always: `python3 "${CLAUDE_PLUGIN_ROOT}/installer/eng_ai.py" <command> --target .` (no `--apply`). Show the user the full output.
2. Stop and ask before applying. On a yes, run the same command with `--apply`, and for `bootstrap` or `update` also `--marketplace rishabhjj/eng-ai-standards`.
3. Repeat every `needs a human:` line back to the user with what to do (see the table in docs/setup.md step 5). Exit code 1 means there is at least one.
4. For `bootstrap` and `update`: run `python3 "${CLAUDE_PLUGIN_ROOT}/installer/eng_ai.py" doctor --target .` and `VERIFY_LIST=1 scripts/verify.sh`. Report every `FAIL` and the detected verify steps. If no steps were detected or nested projects were found, tell the user to list the commands under `verify` in `.eng-ai.json` and offer to draft that list from the repo's build files.
5. Do not commit. Say which files were added and that they should be committed by path, and that each teammate runs `git config core.hooksPath .githooks` once per clone.

Never pass `--apply` without the user's yes. Never edit `.eng-ai.json`, hooks or `.claude/settings.json` by hand to work around a `needs a human` line; the user merges those.
