import importlib.util
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
EVALS = KIT / "evals"
CASES = sorted(p for p in EVALS.iterdir() if p.is_dir() and p.name != "results")
GRADER_TYPES = {"regex", "tool_used", "tool_order", "file_exists", "llm", "baseline"}

spec = importlib.util.spec_from_file_location("build_eval_plugin", KIT / "scripts/build-eval-plugin.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def frontmatter(path):
    m = re.match(r"---\n(.*?)\n---\n?(.*)", path.read_text(), re.S)
    meta = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta


class CaseStructureTest(unittest.TestCase):
    def test_cases_exist(self):
        self.assertGreaterEqual(len(CASES), 4)

    def test_every_case_is_complete(self):
        for case in CASES:
            for rel in ("prompt.md", "case.yaml", "scaffold.sh"):
                self.assertTrue((case / rel).is_file(), f"{case.name}/{rel}")
            self.assertTrue(list((case / "graders").glob("*.md")), f"{case.name} has no graders")
            self.assertIn(f"name: {case.name}", (case / "case.yaml").read_text())
            self.assertIn("scaffold_script: scaffold.sh", (case / "case.yaml").read_text())

    def test_grader_types_are_valid_and_each_case_has_a_non_llm_grader(self):
        for case in CASES:
            types = [frontmatter(g)["type"] for g in (case / "graders").glob("*.md")]
            self.assertTrue(set(types) <= GRADER_TYPES, f"{case.name}: {types}")
            self.assertTrue(set(types) - {"llm", "baseline"}, f"{case.name} relies only on a model judge")

    def test_cases_do_not_need_bash(self):
        for case in CASES:
            tools = frontmatter(case / "prompt.md")["allowed_tools"]
            self.assertNotIn("Bash", tools, case.name)

    def test_regexes_compile(self):
        for case in CASES:
            for g in (case / "graders").glob("*.md"):
                meta = frontmatter(g)
                for key in ("pattern", "input_match"):
                    if key in meta:
                        re.compile(meta[key].strip("'\""))


class FixtureTest(unittest.TestCase):
    def scaffold(self, case):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        subprocess.run(["bash", str(EVALS / case / "scaffold.sh")], cwd=tmp.name, check=True, capture_output=True)
        return Path(tmp.name)

    def test_review_cases_produce_a_nonempty_diff_file(self):
        for case in ("review-catches-sql-injection", "review-clean-diff", "review-catches-swallowed-error"):
            root = self.scaffold(case)
            diff = (root / "changes.diff").read_text()
            self.assertIn("+++ b/", diff, case)

    def test_sql_injection_fixture_contains_the_vulnerable_line(self):
        self.assertIn("f\"select * from users where name = '{name}'\"",
                      (self.scaffold("review-catches-sql-injection") / "changes.diff").read_text())

    def test_clean_diff_fixture_keeps_tests_green_before_and_after(self):
        root = self.scaffold("review-clean-diff")
        run = ["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."]
        self.assertEqual(subprocess.run(run, cwd=root, capture_output=True).returncode, 0)
        subprocess.run(["git", "checkout", "-q", "main"], cwd=root, check=True)
        self.assertEqual(subprocess.run(run, cwd=root, capture_output=True).returncode, 0)

    def test_tdd_bug_actually_reproduces(self):
        root = self.scaffold("tdd-bugfix")
        out = subprocess.run(["python3", "-c", "from calc import apply_discount as f; print(f(200, 10))"],
                             cwd=root, capture_output=True, text=True).stdout.strip()
        self.assertNotEqual(out, "180")
        self.assertIn("200 with a 10 percent discount should give 180", (EVALS / "tdd-bugfix/prompt.md").read_text())


class BuildPluginTest(unittest.TestCase):
    def test_build_contains_manifest_all_skills_and_cases_but_no_results(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "plugin"
            skills = builder.build(out)
            manifest = json.loads((out / ".claude-plugin/plugin.json").read_text())
            self.assertEqual(manifest["name"], "workflow")
            on_disk = {p.name for p in (KIT / ".agents/skills").iterdir() if p.is_dir()}
            self.assertEqual(set(skills), on_disk)
            for name in skills:
                self.assertTrue((out / "skills" / name / "SKILL.md").is_file())
            self.assertEqual({p.name for p in (out / "evals").iterdir()}, {c.name for c in CASES})
            self.assertFalse((out / "evals/results").exists())


if __name__ == "__main__":
    unittest.main()
