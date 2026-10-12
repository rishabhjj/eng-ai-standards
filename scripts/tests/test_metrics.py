import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, KIT / "scripts" / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


metrics = load("metrics", "metrics.py")
export = load("export_pr_data", "export-pr-data.py")
BOX = "- [x] Authored or substantially drafted by an AI agent"


def pr(n, agent=False, labels=(), cr=0, findings=()):
    return {"number": n, "body": BOX if agent else "- [ ] Authored or substantially drafted by an AI agent",
            "labels": list(labels), "changes_requested": cr, "findings": list(findings)}


class SummarizeTest(unittest.TestCase):
    def test_counts_shares_rework_and_break_glass(self):
        s = metrics.summarize([pr(1, agent=True, cr=1), pr(2, agent=True), pr(3, labels=["break-glass"]), pr(4)])
        self.assertEqual((s["prs"], s["agent_authored"]), (4, 2))
        self.assertEqual(s["agent_share"], 0.5)
        self.assertEqual(s["rework_rate_agent"], 0.5)
        self.assertEqual(s["rework_rate_human"], 0.0)
        self.assertEqual(s["break_glass"], 1)

    def test_unchecked_box_is_not_agent_authored(self):
        self.assertEqual(metrics.summarize([pr(1)])["agent_authored"], 0)

    def test_lens_precision_verdicts(self):
        prs = [pr(1, findings=[{"lens": "security", "up": 9, "down": 1}, {"lens": "tests", "up": 2, "down": 8},
                               {"lens": "simplicity", "up": 1, "down": 0}])]
        p = metrics.summarize(prs)["lens_precision"]
        self.assertEqual(p["security"]["verdict"], "keep")
        self.assertEqual(p["tests"]["verdict"], "disable or tighten")
        self.assertEqual(p["simplicity"]["verdict"], "insufficient data")

    def test_votes_aggregate_across_prs_and_thresholds_are_configurable(self):
        prs = [pr(1, findings=[{"lens": "security", "up": 3, "down": 2}]),
               pr(2, findings=[{"lens": "security", "up": 3, "down": 2}])]
        self.assertEqual(metrics.summarize(prs)["lens_precision"]["security"]["verdict"], "disable or tighten")
        self.assertEqual(metrics.summarize(prs, min_precision=0.5)["lens_precision"]["security"]["verdict"], "keep")

    def test_empty_input_does_not_crash(self):
        s = metrics.summarize([])
        self.assertIsNone(s["agent_share"])
        self.assertIn("no reacted findings yet", metrics.render(s))

    def test_cli_reads_a_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "d.json"
            path.write_text(json.dumps({"prs": [pr(1, agent=True)]}))
            self.assertEqual(metrics.main([str(path), "--json"]), 0)


class ExportParsingTest(unittest.TestCase):
    def test_pr_record_extracts_labels_reviews_and_finding_reactions(self):
        record = export.pr_record(
            {"number": 7, "body": BOX, "labels": [{"name": "break-glass"}],
             "reviews": [{"state": "CHANGES_REQUESTED"}, {"state": "APPROVED"}]},
            [{"body": "SQL injection at db.py:12 <!-- eng-ai-finding:security -->", "reactions": {"+1": 3, "-1": 1}},
             {"body": "looks good to me"},
             {"body": "x <!--eng-ai-finding:tests-->", "reactions": {}}])
        self.assertEqual(record["labels"], ["break-glass"])
        self.assertEqual(record["changes_requested"], 1)
        self.assertEqual(record["findings"], [{"lens": "security", "up": 3, "down": 1},
                                              {"lens": "tests", "up": 0, "down": 0}])

    def test_marker_matches_what_the_review_skill_tells_reviewers_to_emit(self):
        text = (KIT / ".agents/skills/review/SKILL.md").read_text()
        example = re.search(r"`(<!-- eng-ai-finding:<lens> -->)`", text).group(1).replace("<lens>", "security")
        self.assertTrue(export.MARKER.search(example))


class SkillInvocationTest(unittest.TestCase):
    AUTO = ("review-spec", "review-postmortem", "grill-with-docs", "to-spec", "to-tickets", "retro")
    USER_ONLY = ("setup-matt-pocock-skills",)

    def test_workflow_skills_are_model_invocable_in_both_tools(self):
        for name in self.AUTO:
            base = KIT / ".agents/skills" / name
            self.assertNotIn("disable-model-invocation: true", (base / "SKILL.md").read_text(), name)
            self.assertIn("allow_implicit_invocation: true", (base / "agents/openai.yaml").read_text(), name)
            self.assertIn(f"name: {name}", (base / "SKILL.md").read_text())

    def test_one_time_setup_stays_user_only(self):
        for name in self.USER_ONLY:
            base = KIT / ".agents/skills" / name
            self.assertIn("disable-model-invocation: true", (base / "SKILL.md").read_text(), name)
            self.assertIn("allow_implicit_invocation: false", (base / "agents/openai.yaml").read_text(), name)

    def test_publishing_skills_ask_first(self):
        self.assertIn("only after an explicit yes", (KIT / ".agents/skills/to-spec/SKILL.md").read_text())
        self.assertIn("until the user approves", (KIT / ".agents/skills/to-tickets/SKILL.md").read_text())

    def test_only_cite_real_rules(self):
        known = {p.name[:7] for p in (KIT / "standards/rules").glob("*.md")}
        for name in ("review-spec", "review-postmortem"):
            ids = set(re.findall(r"\b[A-Z]{3}-\d{3}\b", (KIT / ".agents/skills" / name / "SKILL.md").read_text()))
            self.assertEqual(ids - known, set(), name)


if __name__ == "__main__":
    unittest.main()
