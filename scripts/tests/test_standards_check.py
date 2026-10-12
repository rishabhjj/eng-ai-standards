import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "standards-check.py"
spec = importlib.util.spec_from_file_location("standards_check", SCRIPT)
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)

RULE = """---
id: {id}
title: {title}
status: {status}
severity: high
check: {check}
---
Because reasons.
"""


class Repo:
    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "standards" / "rules").mkdir(parents=True)
        (self.root / sc.LENS_DIR).mkdir(parents=True)
        (self.root / "AGENTS.md").write_text(f"x\n{sc.INDEX_START}\n{sc.INDEX_END}\n")

    def rule(self, id="SEC-001", status="approved", check="review:security", title="t", name=None):
        path = self.root / "standards" / "rules" / (name or f"{id}-t.md")
        path.write_text(RULE.format(id=id, title=title, status=status, check=check))

    def lens(self, name, text):
        (self.root / sc.LENS_DIR / f"{name}.md").write_text(text)

    def hook(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def errors(self):
        return sc.validate(self.root)[1]

    def close(self):
        self._tmp.cleanup()


class ValidateTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.close)

    def test_valid_review_rule_passes(self):
        self.repo.rule()
        self.repo.lens("security", "applies SEC-001")
        self.assertEqual(self.repo.errors(), [])

    def test_lens_must_cite_rule_id(self):
        self.repo.rule()
        self.repo.lens("security", "mentions nothing")
        self.assertIn("never cites SEC-001", self.repo.errors()[0])

    def test_missing_check_target_fails(self):
        self.repo.rule(check="hook:.githooks/nope")
        self.assertIn("does not exist", self.repo.errors()[0])

    def test_unknown_check_type_fails(self):
        self.repo.rule(check="magic:thing")
        self.assertIn("unknown check type", self.repo.errors()[0])

    def test_enforced_needs_non_review_check(self):
        self.repo.rule(status="enforced")
        self.repo.lens("security", "SEC-001")
        self.assertIn("enforced rule cannot rely on a review lens", self.repo.errors()[0])

    def test_enforced_hook_passes(self):
        self.repo.rule(id="GIT-001", status="enforced", check="hook:.githooks/commit-msg")
        self.repo.hook(".githooks/commit-msg", "# GIT-001")
        self.assertEqual(self.repo.errors(), [])

    def test_duplicate_id_and_bad_filename(self):
        self.repo.rule(name="SEC-001-a.md")
        self.repo.rule(name="SEC-001-b.md")
        self.repo.lens("security", "SEC-001")
        self.assertTrue(any("duplicate id" in e for e in self.repo.errors()))
        self.repo.rule(id="SEC-002", name="wrong-name.md")
        self.assertTrue(any("filename must start with" in e for e in self.repo.errors()))

    def test_bad_id_status_severity_and_missing_field(self):
        self.repo.rule(id="sec1", name="sec1-x.md", status="maybe")
        errors = " ".join(self.repo.errors())
        self.assertIn("must look like ABC-123", errors)
        self.assertIn("status must be one of", errors)
        path = self.repo.root / "standards" / "rules" / "SEC-009-x.md"
        path.write_text("---\nid: SEC-009\n---\nbody\n")
        self.assertIn("missing title", " ".join(self.repo.errors()))

    def test_linter_check_needs_reference(self):
        self.repo.rule(check="linter:")
        self.assertIn("needs a reference", self.repo.errors()[0])
        self.repo.rule(check="linter:eslint")
        self.assertIn("must look like linter:<tool>:<rule>", self.repo.errors()[0])

    def test_linter_check_must_be_configured_and_cite_id(self):
        self.repo.rule(check="linter:eslint:no-explicit-any")
        self.assertIn("no file under lint-packs/ configures no-explicit-any", self.repo.errors()[0])
        self.repo.hook("lint-packs/typescript/eslint.mjs", "'no-explicit-any': 'error'")
        self.assertIn("cites SEC-001", self.repo.errors()[0])
        self.repo.hook("lint-packs/typescript/eslint.mjs", "// SEC-001\n'no-explicit-any': 'error'")
        self.assertEqual(self.repo.errors(), [])

    def test_multiple_checks_all_validated_and_enforced_needs_one_non_review(self):
        self.repo.hook("lint-packs/x.toml", "# SEC-001\nS608 = true")
        self.repo.lens("security", "SEC-001")
        self.repo.rule(status="enforced", check="review:security, linter:ruff:S608")
        self.assertEqual(self.repo.errors(), [])
        self.repo.rule(status="enforced", check="review:security, hook:missing.sh")
        self.assertIn("does not exist", self.repo.errors()[0])


class IndexTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.close)
        self.repo.rule(title="no secrets")
        self.repo.lens("security", "SEC-001")

    def test_stale_index_fails_then_write_fixes(self):
        rules, _ = sc.validate(self.repo.root)
        self.assertEqual(len(sc.sync_index(self.repo.root, rules, write=False)), 1)
        self.assertEqual(sc.sync_index(self.repo.root, rules, write=True), [])
        self.assertIn("- SEC-001 [approved] no secrets", (self.repo.root / "AGENTS.md").read_text())
        self.assertEqual(sc.sync_index(self.repo.root, rules, write=False), [])

    def test_missing_markers_fail(self):
        (self.repo.root / "AGENTS.md").write_text("no markers")
        rules, _ = sc.validate(self.repo.root)
        self.assertIn("no <!-- standards:start -->", sc.sync_index(self.repo.root, rules, False)[0])

    def test_main_exit_codes(self):
        self.assertEqual(sc.main(["--root", str(self.repo.root)]), 1)
        self.assertEqual(sc.main(["--root", str(self.repo.root), "--write-index"]), 0)
        self.assertEqual(sc.main(["--root", str(self.repo.root)]), 0)


if __name__ == "__main__":
    unittest.main()
