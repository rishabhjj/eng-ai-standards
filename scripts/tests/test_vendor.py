import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("vendor", KIT / "scripts" / "vendor.py")
vendor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vendor)


def run(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = vendor.main(list(args))
    return code, out.getvalue() + err.getvalue()


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"})


class FakeWorld(unittest.TestCase):
    """A local 'upstream' repo and a consumer root wired through vendor.lock.json."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.up, self.root = base / "up", base / "root"
        (self.up / "skills/eng/alpha").mkdir(parents=True)
        (self.up / "skills/eng/beta").mkdir(parents=True)
        (self.up / "skills/eng/alpha/SKILL.md").write_text("---\nname: alpha\n---\nsee the `code-review` skill\n")
        (self.up / "skills/eng/beta/SKILL.md").write_text("---\nname: beta\n---\nbeta body\n")
        (self.up / "LICENSE").write_text("MIT License\n")
        (self.up / "other.txt").write_text("unrelated\n")
        git(self.up, "init", "-q", "-b", "main")
        git(self.up, "config", "uploadpack.allowAnySHA1InWant", "true")
        git(self.up, "add", ".")
        git(self.up, "commit", "-qm", "init")
        self.root.mkdir()
        self.lock = {"installed": {}, "vendored": {"pack": {
            "repo": f"file://{self.up}", "license": "MIT", "license_file": "LICENSE",
            "skills": {"alpha": "skills/eng/alpha", "beta": "skills/eng/beta"},
            "patches": [{"path": "alpha/SKILL.md", "old": "`code-review`", "new": "`review`"}]}}}
        (self.root / "vendor.lock.json").write_text(json.dumps(self.lock))

    def commit_upstream(self, rel, text):
        (self.up / rel).write_text(text)
        git(self.up, "add", ".")
        git(self.up, "commit", "-qm", "change")

    def update(self):
        return run("update", "--root", str(self.root), "--source", str(self.up))


class VendorTest(FakeWorld):
    def test_update_copies_patches_pins_and_verifies(self):
        code, out = self.update()
        self.assertEqual(code, 0, out)
        alpha = (self.root / ".agents/skills/alpha/SKILL.md").read_text()
        self.assertIn("`review`", alpha)
        self.assertNotIn("code-review", alpha)
        self.assertEqual((self.root / "third_party/pack/LICENSE").read_text(), "MIT License\n")
        lock = vendor.load(self.root)
        self.assertEqual(lock["vendored"]["pack"]["commit"], vendor.git("rev-parse", "HEAD", cwd=self.up))
        self.assertEqual(run("verify", "--root", str(self.root))[0], 0)

    def test_verify_detects_local_edit_extra_and_missing_files(self):
        self.update()
        skill = self.root / ".agents/skills/beta/SKILL.md"
        skill.write_text("---\nname: beta\n---\nedited\n")
        (self.root / ".agents/skills/beta/extra.md").write_text("x")
        (self.root / ".agents/skills/alpha/SKILL.md").unlink()
        code, out = run("verify", "--root", str(self.root))
        self.assertEqual(code, 1)
        self.assertIn("changed locally", out)
        self.assertIn("not in the lock", out)
        self.assertIn("is missing", out)

    def test_verify_detects_name_mismatch_and_missing_license(self):
        self.update()
        (self.root / ".agents/skills/beta/SKILL.md").write_text("---\nname: other\n---\n")
        (self.root / "third_party/pack/LICENSE").unlink()
        lock = vendor.load(self.root)
        lock["vendored"]["pack"]["files"] = {p: vendor.sha(self.root / p)
                                             for p in lock["vendored"]["pack"]["files"]
                                             if (self.root / p).exists()}
        vendor.save(self.root, lock)
        out = run("verify", "--root", str(self.root))[1]
        self.assertIn("name does not match the directory", out)
        self.assertIn("missing third_party/pack/LICENSE", out)

    def test_patch_that_no_longer_applies_fails_update(self):
        self.commit_upstream("skills/eng/alpha/SKILL.md", "---\nname: alpha\n---\nrewritten upstream\n")
        with self.assertRaises(SystemExit) as ctx:
            self.update()
        self.assertIn("patch no longer applies", str(ctx.exception))

    def test_symlink_in_upstream_skill_fails_update(self):
        (self.up / "skills/eng/beta/link.md").symlink_to("../../../LICENSE")
        git(self.up, "add", ".")
        git(self.up, "commit", "-qm", "link")
        with self.assertRaises(SystemExit) as ctx:
            self.update()
        self.assertIn("symlink not allowed in vendored skill: .agents/skills/beta/link.md", str(ctx.exception))

    def test_verify_rejects_symlink_in_vendored_tree(self):
        self.update()
        (self.root / ".agents/skills/beta/link.md").symlink_to(self.root / "vendor.lock.json")
        code, out = run("verify", "--root", str(self.root))
        self.assertEqual(code, 1)
        self.assertIn("symlink not allowed in vendored skill: .agents/skills/beta/link.md", out)

    def test_update_removes_files_deleted_upstream(self):
        self.update()
        self.commit_upstream("skills/eng/beta/extra.md", "x")
        self.update()
        self.assertTrue((self.root / ".agents/skills/beta/extra.md").exists())
        (self.up / "skills/eng/beta/extra.md").unlink()
        git(self.up, "add", "-A")
        git(self.up, "commit", "-qm", "rm")
        self.update()
        self.assertFalse((self.root / ".agents/skills/beta/extra.md").exists())
        self.assertEqual(run("verify", "--root", str(self.root))[0], 0)


class CheckTest(FakeWorld):
    def check(self):
        return run("check", "--root", str(self.root), "--source", f"pack={self.up}")

    def test_up_to_date(self):
        self.update()
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertIn("up to date", out)

    def test_irrelevant_upstream_change_is_not_drift(self):
        self.update()
        self.commit_upstream("other.txt", "changed\n")
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertIn("nothing we use changed", out)

    def test_relevant_upstream_change_is_drift(self):
        self.update()
        self.commit_upstream("skills/eng/beta/SKILL.md", "---\nname: beta\n---\nnew body\n")
        code, out = self.check()
        self.assertEqual(code, 1, out)
        self.assertIn("upstream moved", out)
        self.assertIn("skills/eng/beta/SKILL.md", out)


class RealLockTest(unittest.TestCase):
    def test_real_lock_verifies_offline(self):
        code, out = run("verify")
        self.assertEqual(code, 0, out)

    def test_third_party_file_mentions_every_source(self):
        text = (KIT / "THIRD_PARTY.md").read_text()
        for entry in [*vendor.load(KIT)["vendored"].values(), *vendor.load(KIT)["installed"].values()]:
            self.assertIn(entry["repo"], text)


if __name__ == "__main__":
    unittest.main()
