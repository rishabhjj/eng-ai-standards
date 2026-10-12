import unittest
import tempfile
from pathlib import Path

import test_installer as ti

KIT = ti.KIT
SKILLS = sorted(p.name for p in (KIT / ".agents/skills").iterdir() if (p / "SKILL.md").is_file())


class InstallSkillsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dest = Path(self._tmp.name) / "skills"

    def run_cmd(self, *extra):
        return ti.run("install-skills", "--dest", str(self.dest), *extra)

    def test_dry_run_writes_nothing(self):
        code, out = self.run_cmd()
        self.assertEqual(code, 0)
        self.assertIn("dry run", out)
        self.assertFalse(self.dest.exists())

    def test_apply_copies_every_skill_and_is_idempotent(self):
        self.run_cmd("--apply")
        for name in SKILLS:
            self.assertTrue((self.dest / name / "SKILL.md").is_file(), name)
        self.assertTrue((self.dest / ".eng-ai-managed.json").is_file())
        _, out = self.run_cmd("--apply")
        self.assertNotIn("create", out)
        self.assertNotIn("update", out)
        self.assertNotIn("needs a human", out)

    def test_foreign_skill_with_same_name_is_left_alone(self):
        (self.dest / "tdd").mkdir(parents=True)
        (self.dest / "tdd" / "SKILL.md").write_text("mine")
        _, out = self.run_cmd("--apply")
        self.assertEqual((self.dest / "tdd" / "SKILL.md").read_text(), "mine")
        self.assertIn("tdd already exists", out)
        self.assertTrue((self.dest / "review" / "SKILL.md").is_file())

    def test_other_skills_in_the_folder_are_untouched(self):
        (self.dest / "unrelated").mkdir(parents=True)
        (self.dest / "unrelated" / "SKILL.md").write_text("keep")
        self.run_cmd("--apply")
        self.assertEqual((self.dest / "unrelated" / "SKILL.md").read_text(), "keep")

    def test_locally_edited_installed_skill_is_not_overwritten(self):
        self.run_cmd("--apply")
        (self.dest / "review" / "SKILL.md").write_text("edited")
        _, out = self.run_cmd("--apply")
        self.assertEqual((self.dest / "review" / "SKILL.md").read_text(), "edited")
        self.assertIn("review already exists", out)

    def test_untouched_installed_skill_is_updated_when_the_kit_changes(self):
        self.run_cmd("--apply")
        import json
        manifest = self.dest / ".eng-ai-managed.json"
        old = "# older kit version\n"
        (self.dest / "review" / "SKILL.md").write_text(old)
        recorded = json.loads(manifest.read_text())
        recorded["review"] = ti.eng.tree_hash(self.dest / "review")
        manifest.write_text(json.dumps(recorded))
        _, out = self.run_cmd("--apply")
        self.assertIn("update  review", out)
        self.assertNotEqual((self.dest / "review" / "SKILL.md").read_text(), old)


if __name__ == "__main__":
    unittest.main()
