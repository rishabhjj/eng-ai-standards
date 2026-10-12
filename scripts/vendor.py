#!/usr/bin/env python3
"""Manage third-party skills recorded in vendor.lock.json. Stdlib only.

  verify            offline: vendored files match the lock, licenses present, skill names match dirs
  check             network: report upstream changes since the pinned commit (exit 1 on drift)
  update [--name N] re-copy vendored skills from upstream HEAD, reapply patches, refresh the lock
  relock            offline: refresh file hashes after changing a recorded patch (commit unchanged)

Add --source DIR (a local clone) to avoid cloning, and --root DIR to run against another checkout.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LOCK = "vendor.lock.json"
SKILLS_DIR = Path(".agents/skills")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def git(*args, cwd=None):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def load(root):
    return json.loads((root / LOCK).read_text())


def save(root, lock):
    (root / LOCK).write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")


def vendored_entries(root, entry):
    out = []
    for dest in entry["skills"]:
        base = root / SKILLS_DIR / dest
        out += sorted(base.rglob("*")) if base.is_dir() else []
    return out


def vendored_files(root, entry):
    return [p for p in vendored_entries(root, entry) if p.is_file() and not p.is_symlink()]


def symlinks(root, entry):
    """A symlink can point outside the skill or the repo; vendored trees must be plain files."""
    return [f"symlink not allowed in vendored skill: {p.relative_to(root)}"
            for p in vendored_entries(root, entry) if p.is_symlink()]


def skill_name(skill_md):
    m = re.search(r"^name:\s*(\S+)", skill_md.read_text(), re.M)
    return m.group(1) if m else None


def verify(root):
    lock, errors = load(root), []
    for name, entry in lock["vendored"].items():
        lic = root / "third_party" / name / "LICENSE"
        if not lic.is_file():
            errors.append(f"{name}: missing {lic.relative_to(root)}")
        recorded = entry["files"]
        actual = {str(p.relative_to(root)): sha(p) for p in vendored_files(root, entry)}
        for path, digest in recorded.items():
            if path not in actual:
                errors.append(f"{name}: {path} is missing")
            elif actual[path] != digest:
                errors.append(f"{name}: {path} changed locally; record it as a patch and run update")
        for path in actual.keys() - recorded.keys():
            errors.append(f"{name}: {path} is not in the lock")
        errors += [f"{name}: {e}" for e in symlinks(root, entry)]
        for dest in entry["skills"]:
            md = root / SKILLS_DIR / dest / "SKILL.md"
            if not md.is_file() or skill_name(md) != dest:
                errors.append(f"{name}: {dest}/SKILL.md missing or its name does not match the directory")
    for name, entry in lock.get("installed", {}).items():
        for key in ("repo", "commit", "license", "plugins", "install", "why_not_vendored"):
            if not entry.get(key):
                errors.append(f"{name}: installed entry is missing '{key}'")
    return errors


def upstream_checkout(entry, source, tmp):
    if source:
        return Path(source)
    dest = Path(tmp) / "up"
    git("clone", "--quiet", "--depth", "1", "--", entry["repo"], str(dest))
    return dest


def apply_patches(root, entry):
    for p in entry.get("patches", []):
        path = root / SKILLS_DIR / p["path"]
        text = path.read_text()
        if p["old"] not in text:
            raise SystemExit(f"patch no longer applies to {p['path']}: {p['old']!r} not found upstream")
        path.write_text(text.replace(p["old"], p["new"]))


def update(root, only, source):
    lock = load(root)
    for name, entry in lock["vendored"].items():
        if only and name != only:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            up = upstream_checkout(entry, source, tmp)
            head = git("rev-parse", "HEAD", cwd=up)
            for dest, upstream_path in entry["skills"].items():
                target = root / SKILLS_DIR / dest
                if target.is_dir():
                    shutil.rmtree(target)
                shutil.copytree(up / upstream_path, target, symlinks=True)
            bad = symlinks(root, entry)
            if bad:
                raise SystemExit("\n".join(bad))
            lic = root / "third_party" / name
            lic.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(up / entry["license_file"], lic / "LICENSE")
        apply_patches(root, entry)
        entry["commit"] = head
        entry["files"] = {str(p.relative_to(root)): sha(p) for p in vendored_files(root, entry)}
        print(f"{name}: updated to {head[:12]} ({len(entry['files'])} files)")
    save(root, lock)


def relock(root):
    """Re-hash vendored files after a patch edit. Patches must still apply (verified against the lock)."""
    lock = load(root)
    for name, entry in lock["vendored"].items():
        for p in entry.get("patches", []):
            if p["new"] not in (root / SKILLS_DIR / p["path"]).read_text():
                raise SystemExit(f"{name}: patch for {p['path']} is not applied on disk: {p['new']!r}")
        entry["files"] = {str(p.relative_to(root)): sha(p) for p in vendored_files(root, entry)}
        print(f"{name}: relocked {len(entry['files'])} files at {entry['commit'][:12]}")
    save(root, lock)


def check(root, source):
    lock, drift = load(root), False
    groups = [(n, e, list(e["skills"].values())) for n, e in lock["vendored"].items()]
    groups += [(n, e, [f"plugins/{p}" for p in e["plugins"]]) for n, e in lock.get("installed", {}).items()]
    for name, entry, paths in groups:
        with tempfile.TemporaryDirectory() as tmp:
            up = upstream_checkout(entry, source.get(name) if source else None, tmp)
            head = git("rev-parse", "HEAD", cwd=up)
            if head == entry["commit"]:
                print(f"{name}: up to date at {head[:12]}")
                continue
            have = subprocess.run(["git", "cat-file", "-e", entry["commit"]], cwd=up, capture_output=True)
            if have.returncode:
                git("fetch", "--quiet", "--depth", "1", "origin", entry["commit"], cwd=up)
            stat = git("diff", "--stat", entry["commit"], head, "--", *paths, cwd=up)
            if stat:
                drift = True
                print(f"{name}: upstream moved {entry['commit'][:12]} -> {head[:12]}\n{stat}")
            else:
                print(f"{name}: upstream moved to {head[:12]} but nothing we use changed")
    return 1 if drift else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["verify", "check", "update", "relock"])
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--name")
    ap.add_argument("--source", help="local upstream clone (single-entry update, or per entry as NAME=DIR)", action="append")
    args = ap.parse_args(argv)
    root = Path(args.root)
    sources = dict(s.split("=", 1) for s in args.source or [] if "=" in s)
    single = next((s for s in args.source or [] if "=" not in s), None)
    if args.cmd == "verify":
        errors = verify(root)
        for e in errors:
            print(f"vendor: {e}", file=sys.stderr)
        print("vendor: lock OK" if not errors else f"vendor: {len(errors)} problem(s)")
        return 1 if errors else 0
    if args.cmd == "update":
        update(root, args.name, single)
        return 0
    if args.cmd == "relock":
        relock(root)
        return 0
    return check(root, sources)


if __name__ == "__main__":
    sys.exit(main())
