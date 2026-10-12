#!/usr/bin/env python3
"""eng-ai installer: bootstrap | update | doctor. Stdlib only.

bootstrap/update are dry-run unless --apply. They never overwrite a file the
repo changed, and never edit CLAUDE.md or an existing git hook.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
BLOCK_START, BLOCK_END = "<!-- eng-ai:start -->", "<!-- eng-ai:end -->"
BLOCK_RE = re.compile(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END), re.S)
CONFIG = ".eng-ai.json"
MARKETPLACE = "eng-ai-standards"
PLUGINS = ("guard", "workflow")
# kit source -> target path
MANAGED = {
    "scripts/verify.sh": "scripts/verify.sh",
    ".githooks/commit-msg": ".githooks/commit-msg",
    ".githooks/pre-push": ".githooks/pre-push",
    ".githooks/pre-commit": ".githooks/pre-commit",
    "templates/pull_request_template.md": ".github/pull_request_template.md",
    ".github/workflows/eng-ai-security.yml": ".github/workflows/eng-ai-security.yml",
}
LANG_SUFFIXES = {".kt": "kotlin", ".kts": "kotlin", ".java": "java", ".ts": "typescript",
                 ".tsx": "typescript", ".py": "python"}
LANG_FILES = {"pom.xml": "java", "tsconfig.json": "typescript", "pyproject.toml": "python"}
TOOLS = {"all": ["gitleaks", "semgrep"], "kotlin": ["ktlint"], "python": ["ruff"],
         "typescript": ["node"], "java": ["java"]}
INSTALL_HINTS = {"gitleaks": "brew install gitleaks (https://github.com/gitleaks/gitleaks#installing)",
                 "semgrep": "brew install semgrep (https://semgrep.dev/docs/getting-started/quickstart)",
                 "ruff": "brew install ruff (https://docs.astral.sh/ruff/installation/)",
                 "ktlint": "brew install ktlint (https://pinterest.github.io/ktlint/latest/install/cli/)"}
KIT_HOOKS = ("pre-commit", "commit-msg", "pre-push")
PACK_CONFIGS = {"python": ["ruff.toml", ".ruff.toml", "pyproject.toml"],
                "typescript": ["eslint.config.*", "tsconfig.json"],
                "kotlin": ["build.gradle.kts", "config/detekt*.yml"]}
TOKEN_WARN = 3000  # placeholder budget until we have a measured baseline


def sha(data):
    return hashlib.sha256(data).hexdigest()[:16]


def load_standards():
    spec = importlib.util.spec_from_file_location("standards_check", KIT / "scripts" / "standards-check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# key -> expected type. JSON so every reader (installer, verify.sh, hooks, CI) uses the stdlib parser.
SCHEMA = {"kit_version": str, "languages": list, "marketplace": str, "verify": list, "enforce": list,
          "disabled": list, "exceptions": list, "managed": dict}
EXCEPTION_KEYS = ("rule", "owner", "expires", "reason")


def validate_config(cfg):
    """Return a list of problems; empty when the config matches SCHEMA (COD-006)."""
    if not isinstance(cfg, dict):
        return ["top level must be a JSON object"]
    errors = []
    for key, val in cfg.items():
        want = SCHEMA.get(key)
        if want is None:
            errors.append(f"unknown key '{key}'")
        elif not isinstance(val, want):
            errors.append(f"'{key}' must be a {want.__name__}")
        elif want is list and key != "exceptions" and not all(isinstance(x, str) for x in val):
            errors.append(f"'{key}' must be a list of strings")
    exceptions = cfg.get("exceptions")
    for ex in exceptions if isinstance(exceptions, list) else []:
        if not isinstance(ex, dict) or any(not isinstance(ex.get(k), str) or not ex.get(k) for k in EXCEPTION_KEYS):
            errors.append(f"each exception needs non-empty {', '.join(EXCEPTION_KEYS)}")
        elif not iso_date(ex["expires"]):
            errors.append(f"exception to {ex['rule']}: expires '{ex['expires']}' is not a YYYY-MM-DD date")
    return errors


def iso_date(text):
    try:
        return date.fromisoformat(text) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) else None
    except ValueError:
        return None


def read_config(target):
    path = target / CONFIG
    if not path.is_file():
        return {}
    try:
        cfg = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"{CONFIG} is not valid JSON: {e}")
    errors = validate_config(cfg)
    if errors:
        sys.exit(f"{CONFIG} is invalid: " + "; ".join(errors))
    return cfg


def write_config(target, cfg):
    (target / CONFIG).write_text(json.dumps(cfg, indent=2) + "\n")


def disabled_rules(cfg):
    """Rule IDs switched off for this repo. Security rules cannot be disabled, only given an exception."""
    return {r for r in cfg.get("disabled") or [] if not r.startswith("SEC-")}


def git_files(target):
    r = subprocess.run(["git", "-C", str(target), "ls-files"], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else None


def detect_languages(files):
    found = set()
    for f in files:
        name = Path(f).name
        found.add(LANG_FILES.get(name) or LANG_SUFFIXES.get(Path(f).suffix) or "")
    found.discard("")
    return sorted(found)


def config_languages(cfg, files):
    return cfg.get("languages") or detect_languages(files)


def pack_files(langs, disabled=()):
    """Lint-pack files for the repo's languages (plus semgrep), as kit path -> target path.
    A file named after a disabled rule (e.g. semgrep/ERR-001-*.yml) is left out."""
    out = {}
    for lang in [*langs, "semgrep"]:
        base = KIT / "lint-packs" / lang
        for path in sorted(base.rglob("*")) if base.is_dir() else []:
            if path.is_file() and not path.name.startswith(tuple(f"{r}-" for r in disabled)):
                out[str(path.relative_to(KIT))] = f".eng-ai/lint/{lang}/{path.relative_to(base)}"
    return out


def render_block(cfg=None):
    cfg = cfg or {}
    mod = load_standards()
    rules, _ = mod.load_rules(KIT)
    off = disabled_rules(cfg)
    lines = [f"- {r['id']} [{r['status']}] {r['title']}" for r in rules if r["id"] not in off]
    if off:
        lines.append(f"- Disabled in this repo (do not apply): {', '.join(sorted(off))}")
    for ex in cfg.get("exceptions") or []:
        lines.append(f"- Exception to {ex['rule']} until {ex['expires']} (owner {ex['owner']}): {ex['reason']}")
    index = "\n".join(lines)
    body = (KIT / "templates" / "agents-block.md").read_text().replace("{{RULES}}", index)
    return f"{BLOCK_START}\n{body.rstrip()}\n{BLOCK_END}"


def hooks_path(target):
    r = subprocess.run(["git", "-C", str(target), "config", "core.hooksPath"], capture_output=True, text=True)
    return r.stdout.strip()


def sync_marketplace(target, repo, apply):
    """Declare the plugin marketplace in the repo's .claude/settings.json (add-only merge)."""
    settings = target / ".claude" / "settings.json"
    try:
        data = json.loads(settings.read_text()) if settings.exists() else {}
    except json.JSONDecodeError:
        return [], [".claude/settings.json is not valid JSON; add the eng-ai-standards marketplace by hand"]
    changed = False
    known = data.setdefault("extraKnownMarketplaces", {})
    if MARKETPLACE not in known:
        known[MARKETPLACE] = {"source": {"source": "github", "repo": repo}}
        changed = True
    enabled = data.setdefault("enabledPlugins", {})
    for plugin in PLUGINS:
        if f"{plugin}@{MARKETPLACE}" not in enabled:
            enabled[f"{plugin}@{MARKETPLACE}"] = True
            changed = True
    if not changed:
        return [], []
    kind = "update" if settings.exists() else "create"
    if apply:
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps(data, indent=2) + "\n")
    return [(kind, ".claude/settings.json (eng-ai plugins)")], []


def sync(target, apply, require_config, marketplace=None):
    """Plan (and with apply, perform) the install. Returns (actions, needs_human)."""
    files = git_files(target)
    if files is None:
        sys.exit(f"{target} is not a git repository")
    cfg = read_config(target)
    if require_config and not cfg:
        sys.exit(f"no {CONFIG} in {target}; run bootstrap first")
    managed = dict(cfg.get("managed") or {})
    actions, human = [], []

    langs = config_languages(cfg, files)
    off = disabled_rules(cfg)
    for dst in [d for d in managed if d.startswith(".eng-ai/lint/") and Path(d).name.startswith(
            tuple(f"{r}-" for r in off))]:
        path = target / dst
        if path.is_file() and sha(path.read_bytes()) != managed[dst]:
            human.append(f"{dst} belongs to a disabled rule but was changed locally; delete it by hand")
            continue
        actions.append(("remove", dst))
        if apply and path.is_file():
            path.unlink()
        del managed[dst]
    for src, dst in {**MANAGED, **pack_files(langs, off)}.items():
        data = (KIT / src).read_bytes()
        path = target / dst
        if not path.exists() and dst in managed:
            human.append(f"{dst} was removed locally; delete its entry from 'managed' in {CONFIG} to reinstall it")
            continue
        if not path.exists():
            actions.append(("create", dst))
            if apply:
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(KIT / src, path)  # keeps the executable bit
            managed[dst] = sha(data)
            continue
        current = sha(path.read_bytes())
        if current == sha(data):
            managed[dst] = current
        elif managed.get(dst) == current:
            actions.append(("update", dst))
            if apply:
                path.write_bytes(data)
            managed[dst] = sha(data)
        else:
            human.append(f"{dst} differs from the kit version and was changed locally; merge by hand "
                         f"(e.g. call the kit hook from your existing one)")

    block = render_block(cfg)
    agents = target / "AGENTS.md"
    if not agents.exists():
        actions.append(("create", "AGENTS.md"))
        text = f"# AGENTS.md\n\n<!-- Repo-specific rules go here, outside the managed block. -->\n\n{block}\n"
    elif BLOCK_RE.search(agents.read_text()):
        text = BLOCK_RE.sub(lambda _: block, agents.read_text())
        if text != agents.read_text():
            actions.append(("update", "AGENTS.md managed block"))
    else:
        actions.append(("append", "AGENTS.md managed block"))
        text = agents.read_text().rstrip() + f"\n\n{block}\n"
    if apply and any(a[1].startswith("AGENTS.md") for a in actions):
        agents.write_text(text)

    claude = target / "CLAUDE.md"
    if not claude.exists():
        actions.append(("create", "CLAUDE.md"))
        if apply:
            claude.write_text("@AGENTS.md\n")
    elif "@AGENTS.md" not in claude.read_text():
        human.append("CLAUDE.md exists and does not import AGENTS.md, so Claude will ignore the managed block. "
                     "Add '@AGENTS.md' on its first line, or merge the two files")

    current_hooks = hooks_path(target)
    if not current_hooks:
        actions.append(("config", "git config core.hooksPath .githooks"))
        if apply:
            subprocess.run(["git", "-C", str(target), "config", "core.hooksPath", ".githooks"], check=True)
    elif current_hooks != ".githooks" and not delegates_to_kit(target, current_hooks):
        human.append(f"core.hooksPath is '{current_hooks}', not .githooks; call the kit hooks from it")
    if shutil.which("gitleaks") is None:
        human.append(f"gitleaks is not on PATH; every commit will be blocked until you install it "
                     f"({INSTALL_HINTS['gitleaks']})")

    repo = marketplace or cfg.get("marketplace")
    if repo:
        more_actions, more_human = sync_marketplace(target, repo, apply)
        actions += more_actions
        human += more_human
        cfg["marketplace"] = repo

    if apply:
        cfg["kit_version"] = (KIT / "VERSION").read_text().strip()
        cfg["managed"] = managed
        write_config(target, cfg)
    actions.append(("write", CONFIG))
    if apply and not verify_detects(target):
        human.append("verify.sh detects no checks (or found nested projects); pushes will be blocked until you add "
                     f"a 'verify' list to {CONFIG}")
    return actions, human


def delegates_to_kit(target, hooks_dir):
    """True when every kit hook exists under hooks_dir and calls the .githooks/ one."""
    return all((target / hooks_dir / h).is_file() and ".githooks/" in (target / hooks_dir / h).read_text(errors="ignore")
               for h in KIT_HOOKS)


def verify_detects(target):
    r = subprocess.run(["bash", "scripts/verify.sh"], cwd=target, env={**os.environ, "VERIFY_LIST": "1"},
                       capture_output=True)
    return r.returncode == 0


def cmd_sync(args, require_config):
    target = Path(args.target).resolve()
    actions, human = sync(target, args.apply, require_config, args.marketplace)
    verb = "applied" if args.apply else "would do (dry run, pass --apply)"
    print(f"{verb}:")
    for kind, what in actions:
        print(f"  {kind:7} {what}")
    for msg in human:
        print(f"needs a human: {msg}")
    print(f"next: python3 {Path(__file__).resolve()} doctor")
    return 1 if human else 0


def estimate_tokens(target):
    text = (target / "AGENTS.md").read_text() if (target / "AGENTS.md").is_file() else ""
    skills = set()
    for d in (".agents/skills", ".claude/skills"):
        base = target / d
        if base.is_dir():
            skills |= {p.resolve() for p in base.iterdir() if p.is_dir()}
    return len(text) // 4 + len(skills) * 50, len(skills)  # 50/skill: measured by `claude plugin details`


def cmd_uninstall(args):
    """Remove what bootstrap added and nothing else: managed files whose hash still matches, the AGENTS.md
    block, the one-line CLAUDE.md, the hooksPath setting, the plugin entries and the config. Locally changed
    files are listed and left in place."""
    target = Path(args.target).resolve()
    cfg = read_config(target)
    if not cfg:
        sys.exit(f"no {CONFIG} in {target}; nothing to uninstall")
    actions, human = [], []
    for dst, recorded in sorted((cfg.get("managed") or {}).items()):
        path = target / dst
        if not path.is_file():
            continue
        if sha(path.read_bytes()) != recorded:
            human.append(f"{dst} was changed locally; left in place")
            continue
        actions.append(("remove", dst))
        if args.apply:
            path.unlink()
            for parent in path.parents:
                if parent == target or any(parent.iterdir()):
                    break
                parent.rmdir()
    agents = target / "AGENTS.md"
    if agents.is_file() and BLOCK_RE.search(agents.read_text()):
        text = BLOCK_RE.sub("", agents.read_text()).rstrip() + "\n"
        if text.strip() in ("# AGENTS.md", "# AGENTS.md\n\n<!-- Repo-specific rules go here, outside the managed block. -->"):
            actions.append(("remove", "AGENTS.md"))
            if args.apply:
                agents.unlink()
        else:
            actions.append(("update", "AGENTS.md managed block removed"))
            if args.apply:
                agents.write_text(text)
    claude = target / "CLAUDE.md"
    if claude.is_file() and claude.read_text().strip() == "@AGENTS.md":
        actions.append(("remove", "CLAUDE.md"))
        if args.apply:
            claude.unlink()
    if hooks_path(target) == ".githooks":
        actions.append(("config", "git config --unset core.hooksPath"))
        if args.apply:
            subprocess.run(["git", "-C", str(target), "config", "--unset", "core.hooksPath"], check=True)
    settings = target / ".claude" / "settings.json"
    if settings.is_file():
        try:
            data = json.loads(settings.read_text())
            changed = bool(data.get("extraKnownMarketplaces", {}).pop(MARKETPLACE, None))
            for plugin in PLUGINS:
                changed |= data.get("enabledPlugins", {}).pop(f"{plugin}@{MARKETPLACE}", None) is not None
            if changed:
                actions.append(("update", ".claude/settings.json (eng-ai plugins removed)"))
                if args.apply:
                    settings.write_text(json.dumps(data, indent=2) + "\n")
        except json.JSONDecodeError:
            human.append(".claude/settings.json is not valid JSON; remove the eng-ai-standards entries by hand")
    actions.append(("remove", CONFIG))
    if args.apply:
        (target / CONFIG).unlink()
    print(f"{'applied' if args.apply else 'would do (dry run, pass --apply)'}:")
    for kind, what in actions:
        print(f"  {kind:7} {what}")
    for msg in human:
        print(f"needs a human: {msg}")
    print("not touched: your own AGENTS.md text, lint configs that extend .eng-ai/lint, installed plugins "
          "(claude plugin uninstall guard@eng-ai-standards workflow@eng-ai-standards)")
    return 1 if human else 0


def cmd_doctor(args):
    target = Path(args.target).resolve()
    results = []

    def add(level, msg):
        results.append((level, msg))

    cfg = read_config(target)
    add("ok" if cfg else "fail", f"{CONFIG} present" if cfg else f"{CONFIG} missing; run bootstrap")
    agents = target / "AGENTS.md"
    if not agents.is_file():
        add("fail", "AGENTS.md missing")
    else:
        text = agents.read_text()
        add("ok" if BLOCK_RE.search(text) else "fail", "AGENTS.md managed block present"
            if BLOCK_RE.search(text) else "AGENTS.md has no managed block")
        lines = len(text.splitlines())
        add("ok" if lines <= 100 else "warn", f"AGENTS.md is {lines} lines (limit 100)")
        if BLOCK_RE.search(text) and BLOCK_RE.search(text).group(0) != render_block(cfg):
            add("warn", "managed block is stale; run update")
    claude = target / "CLAUDE.md"
    if claude.is_file() and "@AGENTS.md" not in claude.read_text():
        add("fail", "CLAUDE.md does not import AGENTS.md")
    verify = target / "scripts" / "verify.sh"
    add("ok" if verify.is_file() and os.access(verify, os.X_OK) else "fail", "scripts/verify.sh executable"
        if verify.is_file() and os.access(verify, os.X_OK) else "scripts/verify.sh missing or not executable")
    hooks = hooks_path(target)
    if hooks == ".githooks":
        add("ok", "core.hooksPath is .githooks")
    elif not hooks:
        add("fail", "core.hooksPath is unset; expected .githooks")
    elif delegates_to_kit(target, hooks):
        add("ok", f"core.hooksPath is '{hooks}' and delegates to .githooks")
    else:
        add("warn", f"core.hooksPath is '{hooks}', not .githooks; call the kit hooks from it")
    for dst, recorded in sorted((cfg.get("managed") or {}).items()):
        path = target / dst
        if path.is_file() and sha(path.read_bytes()) != recorded:
            add("warn", f"{dst} modified locally; update will skip it")
    langs = config_languages(cfg, git_files(target) or [])
    for lang in langs:
        configs = [p for pat in PACK_CONFIGS.get(lang, []) for p in target.glob(pat)]
        if not configs:
            continue
        uses = any(".eng-ai/lint" in p.read_text(errors="ignore") for p in configs)
        add("ok" if uses else "warn", f"{lang} config extends the base lint pack" if uses
            else f"{lang} config does not extend .eng-ai/lint/{lang}; see lint-packs/README.md")
    for tool in TOOLS["all"] + [t for lang in langs for t in TOOLS.get(lang, [])]:
        if not shutil.which(tool):
            level = "fail" if tool == "gitleaks" else "warn"
            add(level, f"{tool} not on PATH; install: {INSTALL_HINTS.get(tool, 'see its docs')}")
    kit = (KIT / "VERSION").read_text().strip()
    if cfg and cfg.get("kit_version") != kit:
        add("warn", f"installed with kit {cfg.get('kit_version')}, this kit is {kit}; run update")
    for item in cfg.get("disabled") or []:
        if item.startswith("SEC-"):
            add("fail", f"{item} cannot be disabled; security rules need an entry in 'exceptions' instead")
        else:
            add("warn", f"disabled: {item}")
    for ex in cfg.get("exceptions") or []:
        expired = iso_date(ex["expires"]) < date.today()
        add("fail" if expired else "warn", f"exception to {ex['rule']} (owner {ex['owner']}) "
            + (f"expired on {ex['expires']}; renew or remove it" if expired else f"until {ex['expires']}"))
    repo = cfg.get("marketplace")
    if repo:
        settings = target / ".claude" / "settings.json"
        try:
            on = json.loads(settings.read_text()).get("enabledPlugins", {}) if settings.exists() else {}
        except json.JSONDecodeError:
            on = {}
        missing = [p for p in PLUGINS if not on.get(f"{p}@{MARKETPLACE}")]
        add("ok" if not missing else "warn", "eng-ai plugins enabled in .claude/settings.json" if not missing
            else f"plugins not enabled for the project: {', '.join(missing)}; run update")
    tokens, nskills = estimate_tokens(target)
    add("ok" if tokens <= TOKEN_WARN else "warn",
        f"always-loaded footprint about {tokens} tokens ({nskills} skills); budget {TOKEN_WARN} is a placeholder")

    for level, msg in results:
        print(f"{level.upper():5} {msg}")
    return 1 if any(level == "fail" for level, _ in results) else 0


def tree_hash(directory):
    files = {str(f.relative_to(directory)): sha(f.read_bytes()) for f in sorted(directory.rglob("*")) if f.is_file()}
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:16]


def cmd_install_skills(args):
    """Copy the kit's skills into a user-level skills folder read by Codex and Cursor. Add-only."""
    dest = Path(args.dest).expanduser()
    manifest = dest / ".eng-ai-managed.json"
    recorded = json.loads(manifest.read_text()) if manifest.exists() else {}
    actions, human = [], []
    for skill in sorted(p for p in (KIT / ".agents/skills").iterdir() if (p / "SKILL.md").is_file()):
        wanted, target = tree_hash(skill), dest / skill.name
        if not target.exists():
            actions.append(("create", skill.name))
        else:
            current = tree_hash(target)
            if current == wanted:
                recorded[skill.name] = wanted
                continue
            if recorded.get(skill.name) != current:
                human.append(f"{skill.name} already exists in {dest} and was not installed by eng-ai (or was edited); "
                             f"left alone")
                continue
            actions.append(("update", skill.name))
        if args.apply:
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(skill, target)
        recorded[skill.name] = wanted
    if args.apply:
        dest.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(recorded, indent=2, sort_keys=True) + "\n")
    print(f"{'applied' if args.apply else 'would do (dry run, pass --apply)'} in {dest}:")
    for kind, name in actions:
        print(f"  {kind:7} {name}")
    for msg in human:
        print(f"needs a human: {msg}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="eng-ai")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("bootstrap", "update", "doctor", "uninstall"):
        p = sub.add_parser(name)
        p.add_argument("--target", default=".")
        if name != "doctor":
            p.add_argument("--apply", action="store_true")
        if name in ("bootstrap", "update"):
            p.add_argument("--marketplace", metavar="OWNER/REPO",
                           help="GitHub repo hosting the eng-ai-standards marketplace; enables its plugins for the project")
    skills = sub.add_parser("install-skills", help="copy the kit's skills to ~/.agents/skills (Codex, Cursor)")
    skills.add_argument("--dest", default="~/.agents/skills")
    skills.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "install-skills":
        return cmd_install_skills(args)
    if args.cmd == "doctor":
        return cmd_doctor(args)
    if args.cmd == "uninstall":
        return cmd_uninstall(args)
    return cmd_sync(args, require_config=args.cmd == "update")


if __name__ == "__main__":
    sys.exit(main())
