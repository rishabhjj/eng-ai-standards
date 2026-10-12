import json
import re
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
DOCS = [KIT / "README.md", KIT / "THIRD_PARTY.md", *sorted((KIT / "docs").glob("*.md")),
        KIT / "standards/README.md", KIT / "lint-packs/README.md", KIT / "evals/README.md"]


class LinkTest(unittest.TestCase):
    def test_relative_markdown_links_resolve(self):
        for doc in DOCS:
            for target in re.findall(r"\]\((?!https?://|#|mailto:)([^)\s]+)\)", doc.read_text()):
                path = (doc.parent / target.split("#")[0]).resolve()
                self.assertTrue(path.exists(), f"{doc.relative_to(KIT)} links to missing {target}")

    def test_install_doc_anchor_used_by_readme_exists(self):
        self.assertIn("## Verified so far", (KIT / "docs/setup.md").read_text())


class CodeownersTest(unittest.TestCase):
    def test_every_path_exists_and_critical_paths_are_covered(self):
        paths = [line.split()[0] for line in (KIT / "CODEOWNERS").read_text().splitlines()
                 if line.strip() and not line.startswith("#")]
        for p in paths:
            if p != "*":
                self.assertTrue((KIT / p.lstrip("/")).exists(), p)
        for critical in ("/.claude/hooks/", "/.claude-plugin/", "/installer/", "/standards/", "/vendor.lock.json"):
            self.assertIn(critical, paths)


class RenovateTest(unittest.TestCase):
    cfg = json.loads((KIT / "renovate.json").read_text())

    def extract(self, datasource, text):
        out = []
        for mgr in self.cfg["customManagers"]:
            if mgr["datasourceTemplate"] != datasource:
                continue
            for pattern in mgr["matchStrings"]:
                for m in re.finditer(pattern.replace("(?<", "(?P<"), text):
                    out.append((m.group("depName"), m.group("currentValue")))
        return out

    def workflows(self):
        return "\n".join(p.read_text() for p in KIT.glob(".github/workflows/*.yml"))

    def test_go_install_pins_are_found(self):
        found = dict(self.extract("go", self.workflows()))
        self.assertEqual(found["github.com/zricethezav/gitleaks/v8"], "v8.30.1")
        self.assertIn("github.com/google/osv-scanner/v2/cmd/osv-scanner", found)
        self.assertIn("github.com/rhysd/actionlint/cmd/actionlint", found)

    def test_pypi_pins_are_found(self):
        found = dict(self.extract("pypi", self.workflows()))
        self.assertEqual(found["semgrep"], "1.180.0")
        self.assertIn("zizmor", found)

    def test_file_patterns_cover_the_workflows_and_templates(self):
        for mgr in self.cfg["customManagers"]:
            regexes = [p.strip("/") for p in mgr["managerFilePatterns"]]
            for rel in (".github/workflows/eng-ai-security.yml",):
                self.assertTrue(any(re.search(r, rel) for r in regexes), rel)

    def test_action_digest_pinning_enabled(self):
        self.assertIn("helpers:pinGitHubActionDigests", self.cfg["extends"])


class WorkingRulesTest(unittest.TestCase):
    @staticmethod
    def items(path):
        section = re.search(r"## Working rules\n(.*?)(?:\n## |\Z)", path.read_text(), re.S).group(1)
        return re.findall(r"^\d+\.\s*(.+)$", section, re.M)

    def test_agents_md_working_rules_match_the_template(self):
        kit, template = self.items(KIT / "AGENTS.md"), self.items(KIT / "templates/agents-block.md")
        self.assertTrue(kit)
        self.assertEqual(kit, template)


class ReviewSkillTest(unittest.TestCase):
    def test_languages_checklist_exists_and_is_referenced(self):
        self.assertTrue((KIT / ".agents/skills/review/languages.md").is_file())
        self.assertIn("languages.md", (KIT / ".agents/skills/review/SKILL.md").read_text())

    def test_languages_checklist_cites_only_real_rules(self):
        ids = set(re.findall(r"\b[A-Z]{3}-\d{3}\b", (KIT / ".agents/skills/review/languages.md").read_text()))
        known = {p.name[:7] for p in (KIT / "standards/rules").glob("*.md")}
        self.assertTrue(ids)
        self.assertEqual(ids - known, set())


if __name__ == "__main__":
    unittest.main()
