#!/usr/bin/env python3
"""Validate standards/rules/*.md and keep the AGENTS.md rule index in sync.

Usage: standards-check.py [--root DIR] [--write-index]
Exit 1 on any violation. Stdlib only.
"""
import argparse
import re
import sys
from pathlib import Path

STATUSES = {"approved", "enforced"}
SEVERITIES = {"critical", "high", "medium", "low"}
REQUIRED = ("id", "title", "status", "severity", "check")
ID_RE = re.compile(r"^[A-Z]{3}-\d{3}$")
PATH_CHECKS = {"hook", "semgrep", "ci"}
INDEX_START, INDEX_END = "<!-- standards:start -->", "<!-- standards:end -->"
LENS_DIR = Path(".agents/skills/review/lenses")


def parse_rule(path):
    text = path.read_text()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        return None, "missing frontmatter"
    meta = {}
    for line in m.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    meta["body"] = m.group(2).strip()
    return meta, None


def load_rules(root):
    rules, errors = [], []
    for path in sorted((root / "standards" / "rules").glob("*.md")):
        meta, err = parse_rule(path)
        if err:
            errors.append(f"{path.name}: {err}")
            continue
        meta["_file"] = path.name
        rules.append(meta)
    return rules, errors


def split_checks(rule):
    return [c.strip() for c in rule["check"].split(",") if c.strip()]


def lint_pack_cites(root, rule_name, rid):
    for path in (root / "lint-packs").rglob("*"):
        if path.is_file():
            text = path.read_text()
            if rule_name in text and re.search(rf"\b{rid}\b", text):
                return True
    return False


def check_target(root, rule, check):
    """Return an error string for a bad `check`, else None."""
    kind, _, ref = check.partition(":")
    rid = rule["id"]
    if kind not in {"review", "linter"} | PATH_CHECKS:
        return f"unknown check type '{kind}'"
    if not ref:
        return f"check '{check}' needs a reference after ':'"
    if kind == "linter":
        _tool, _, rule_name = ref.partition(":")
        if not rule_name:
            return f"check '{check}' must look like linter:<tool>:<rule>"
        if not lint_pack_cites(root, rule_name, rid):
            return f"no file under lint-packs/ configures {rule_name} and cites {rid}"
        return None
    target = root / LENS_DIR / f"{ref}.md" if kind == "review" else root / ref
    if not target.is_file():
        return f"check target {target.relative_to(root)} does not exist"
    if not re.search(rf"\b{rid}\b", target.read_text()):
        return f"check target {target.relative_to(root)} never cites {rid}"
    return None


def validate(root):
    rules, errors = load_rules(root)
    seen = {}
    for r in rules:
        name, rid = r["_file"], r.get("id", "")
        miss = [f for f in REQUIRED if not r.get(f)]
        if miss:
            errors.append(f"{name}: missing {', '.join(miss)}")
            continue
        if not ID_RE.match(rid):
            errors.append(f"{name}: id '{rid}' must look like ABC-123")
        if not name.startswith(rid + "-"):
            errors.append(f"{name}: filename must start with '{rid}-'")
        if rid in seen:
            errors.append(f"{name}: duplicate id {rid} (also {seen[rid]})")
        seen[rid] = name
        if r["status"] not in STATUSES:
            errors.append(f"{name}: status must be one of {sorted(STATUSES)}")
        if r["severity"] not in SEVERITIES:
            errors.append(f"{name}: severity must be one of {sorted(SEVERITIES)}")
        if not r["body"]:
            errors.append(f"{name}: body (the why) is empty")
        checks = split_checks(r)
        for check in checks:
            err = check_target(root, r, check)
            if err:
                errors.append(f"{name}: {err}")
        if r["status"] == "enforced" and all(c.startswith("review:") for c in checks):
            errors.append(f"{name}: enforced rule cannot rely on a review lens alone")
    return rules, errors


def render_index(rules):
    lines = [f"- {r['id']} [{r['status']}] {r['title']}" for r in rules]
    return "\n".join([INDEX_START, *lines, INDEX_END])


def sync_index(root, rules, write):
    agents = root / "AGENTS.md"
    if not agents.is_file():
        return ["AGENTS.md is missing"]
    text = agents.read_text()
    block = re.compile(re.escape(INDEX_START) + r".*?" + re.escape(INDEX_END), re.S)
    if not block.search(text):
        return [f"AGENTS.md has no {INDEX_START} ... {INDEX_END} block"]
    fresh = block.sub(lambda _: render_index(rules), text)
    if fresh == text:
        return []
    if write:
        agents.write_text(fresh)
        print("AGENTS.md rule index updated")
        return []
    return ["AGENTS.md rule index is stale; run scripts/standards-check.py --write-index"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--write-index", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root)
    rules, errors = validate(root)
    if not errors:
        errors += sync_index(root, rules, args.write_index)
    for e in errors:
        print(f"standards-check: {e}", file=sys.stderr)
    if not errors:
        enforced = sum(r["status"] == "enforced" for r in rules)
        print(f"standards-check: {len(rules)} rules OK ({enforced} enforced)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
