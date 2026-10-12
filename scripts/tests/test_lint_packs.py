import re
import unittest
from pathlib import Path

import test_installer as ti

KIT = Path(__file__).resolve().parents[2]
SEMGREP = sorted((KIT / "lint-packs" / "semgrep").glob("*.yml"))


class SemgrepStructureTest(unittest.TestCase):
    """Structural only: semgrep itself is not installed, so patterns are not exercised."""

    def test_each_file_cites_its_rule_and_each_rule_is_complete(self):
        self.assertGreaterEqual(len(SEMGREP), 3)
        for path in SEMGREP:
            rule_id = re.match(r"([A-Z]{3}-\d{3})-", path.name).group(1)
            text = path.read_text()
            self.assertIn(rule_id, text, path.name)
            blocks = re.split(r"\n  - id: ", text)[1:]
            self.assertTrue(blocks, f"{path.name} has no rules")
            for block in blocks:
                for key in ("languages:", "severity:", "message:"):
                    self.assertIn(key, block, f"{path.name}: {block.splitlines()[0]} missing {key}")
                self.assertTrue(re.search(r"\bpatterns?(-either)?:", block), path.name)
                self.assertIn(f"standard: {rule_id}", block)

    def test_every_rule_has_a_firing_and_a_safe_fixture(self):
        fixtures = "\n".join(p.read_text() for p in (KIT / "lint-packs" / "semgrep-tests").iterdir())
        for rule_id in (i for p in SEMGREP for i in re.findall(r"- id: (\S+)", p.read_text())):
            self.assertIn(f"ruleid: {rule_id}", fixtures, rule_id)
            self.assertIn(f"ok: {rule_id}", fixtures, rule_id)

    def test_rule_ids_are_unique(self):
        ids = [i for p in SEMGREP for i in re.findall(r"- id: (\S+)", p.read_text())]
        self.assertEqual(len(ids), len(set(ids)))


class InstallPacksTest(ti.TargetRepo):
    def test_python_repo_gets_python_and_semgrep_packs_only(self):
        self.write("a.py", "")
        self.bootstrap("--apply")
        base = self.t / ".eng-ai/lint"
        self.assertTrue((base / "python/ruff.toml").is_file())
        self.assertTrue((base / "python/mypy.ini").is_file())
        self.assertTrue((base / "semgrep/SEC-004-injection.yml").is_file())
        self.assertFalse((base / "typescript").exists())
        self.assertFalse((base / "kotlin").exists())

    def test_multi_language_and_idempotent(self):
        self.write("a.kt", "")
        self.write("web/tsconfig.json", "{}")
        self.bootstrap("--apply")
        base = self.t / ".eng-ai/lint"
        self.assertTrue((base / "kotlin/detekt.yml").is_file())
        self.assertTrue((base / "typescript/eslint.config.mjs").is_file())
        _, out = self.bootstrap("--apply")
        self.assertNotIn("create", out)

    def test_locally_edited_pack_file_is_kept(self):
        self.write("a.py", "")
        self.bootstrap("--apply")
        ruff = self.t / ".eng-ai/lint/python/ruff.toml"
        ruff.write_text("# mine\n")
        _, out = ti.run("update", "--target", str(self.t), "--apply")
        self.assertEqual(ruff.read_text(), "# mine\n")
        self.assertIn(".eng-ai/lint/python/ruff.toml differs", out)

    def test_doctor_checks_repo_extends_pack(self):
        self.write("a.py", "")
        self.write("ruff.toml", "line-length = 100\n")
        self.bootstrap("--apply")
        _, out = ti.run("doctor", "--target", str(self.t))
        self.assertIn("WARN  python config does not extend .eng-ai/lint/python", out)
        (self.t / "ruff.toml").write_text('extend = ".eng-ai/lint/python/ruff.toml"\n')
        _, out = ti.run("doctor", "--target", str(self.t))
        self.assertIn("OK    python config extends the base lint pack", out)


if __name__ == "__main__":
    unittest.main()
