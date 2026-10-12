#!/usr/bin/env python3
"""Assemble a throwaway Claude plugin for `claude plugin eval` from the kit's skills and eval cases.

The repo root is a marketplace, not a plugin, and plugin paths cannot reach outside the plugin
directory, so the skills and cases are copied into build/eval-plugin. Usage: build-eval-plugin.py [OUT]
"""
import json
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent


def build(out):
    out = Path(out)
    if out.exists():
        shutil.rmtree(out)
    (out / ".claude-plugin").mkdir(parents=True)
    skills = sorted(p.name for p in (KIT / ".agents/skills").iterdir() if (p / "SKILL.md").is_file())
    for name in skills:
        shutil.copytree(KIT / ".agents/skills" / name, out / "skills" / name)
    (out / ".claude-plugin/plugin.json").write_text(json.dumps({
        "name": "workflow",
        "version": (KIT / "VERSION").read_text().strip(),
        "description": "eng-ai-standards workflow skills, assembled for evals",
    }, indent=2) + "\n")
    shutil.copytree(KIT / "evals", out / "evals", ignore=shutil.ignore_patterns("results", "README.md"))
    return skills


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else KIT / "build" / "eval-plugin")
    built = build(target)
    print(f"built {target} with {len(built)} skills")
