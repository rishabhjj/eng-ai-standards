import json
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

import test_installer as ti

KIT = Path(__file__).resolve().parents[2]
MARKET = json.loads((KIT / ".claude-plugin/marketplace.json").read_text())
PLUGINS = {p["name"]: p for p in MARKET["plugins"]}


class ManifestTest(unittest.TestCase):
    def test_versions_match_the_release_file(self):
        version = (KIT / "VERSION").read_text().strip()
        for plugin in MARKET["plugins"]:
            self.assertEqual(plugin["version"], version, plugin["name"])

    def test_every_listed_skill_exists_and_every_skill_is_listed(self):
        listed = {Path(s).name for s in PLUGINS["workflow"]["skills"]}
        on_disk = {p.name for p in (KIT / ".agents/skills").iterdir() if p.is_dir()}
        self.assertEqual(listed, on_disk)
        for s in PLUGINS["workflow"]["skills"]:
            self.assertTrue((KIT / s / "SKILL.md").is_file(), s)

    def test_hook_scripts_exist_and_parse(self):
        commands = [h["command"] for ev in PLUGINS["guard"]["hooks"].values() for m in ev for h in m["hooks"]]
        self.assertEqual(len(commands), 4)
        for cmd in commands:
            script = re.search(r'\$\{CLAUDE_PLUGIN_ROOT\}/(\S+?)"', cmd).group(1)
            path = KIT / script
            self.assertTrue(path.is_file(), script)
            subprocess.run(["bash", "-n", str(path)], check=True)

    def test_guard_has_hooks_only_and_workflow_has_no_hooks(self):
        self.assertNotIn("skills", PLUGINS["guard"])
        self.assertNotIn("hooks", PLUGINS["workflow"])

    def test_no_second_reviewer_is_listed(self):
        names = {Path(s).name for s in PLUGINS["workflow"]["skills"]}
        self.assertFalse({"code-review", "implement", "pr"} & names)


class MarketplaceSyncTest(ti.TargetRepo):
    def settings(self):
        return json.loads((self.t / ".claude/settings.json").read_text())

    def test_creates_settings_with_marketplace_and_plugins(self):
        self.bootstrap("--apply", "--marketplace", "acme/eng-ai-standards")
        s = self.settings()
        self.assertEqual(s["extraKnownMarketplaces"]["eng-ai-standards"]["source"],
                         {"source": "github", "repo": "acme/eng-ai-standards"})
        self.assertTrue(s["enabledPlugins"]["guard@eng-ai-standards"])
        self.assertTrue(s["enabledPlugins"]["workflow@eng-ai-standards"])
        self.assertEqual(ti.eng.read_config(self.t)["marketplace"], "acme/eng-ai-standards")

    def test_merge_keeps_existing_settings_and_respects_a_disabled_plugin(self):
        self.write(".claude/settings.json", json.dumps({
            "permissions": {"allow": ["Bash(ls)"]},
            "enabledPlugins": {"workflow@eng-ai-standards": False}}))
        self.bootstrap("--apply", "--marketplace", "acme/eng-ai-standards")
        s = self.settings()
        self.assertEqual(s["permissions"], {"allow": ["Bash(ls)"]})
        self.assertFalse(s["enabledPlugins"]["workflow@eng-ai-standards"])
        self.assertTrue(s["enabledPlugins"]["guard@eng-ai-standards"])

    def test_invalid_json_is_flagged_and_left_alone(self):
        self.write(".claude/settings.json", "{not json")
        _, out = self.bootstrap("--apply", "--marketplace", "acme/x")
        self.assertIn("not valid JSON", out)
        self.assertEqual((self.t / ".claude/settings.json").read_text(), "{not json")

    def test_dry_run_writes_nothing_and_update_reuses_recorded_marketplace(self):
        _, out = self.bootstrap("--marketplace", "acme/x")
        self.assertIn(".claude/settings.json (eng-ai plugins)", out)
        self.assertFalse((self.t / ".claude").exists())
        self.bootstrap("--apply", "--marketplace", "acme/x")
        (self.t / ".claude/settings.json").unlink()
        ti.run("update", "--target", str(self.t), "--apply")
        self.assertTrue(self.settings()["enabledPlugins"]["guard@eng-ai-standards"])

    def test_no_marketplace_option_leaves_claude_dir_alone(self):
        self.bootstrap("--apply")
        self.assertFalse((self.t / ".claude").exists())

    def test_doctor_warns_when_plugins_not_enabled(self):
        self.bootstrap("--apply", "--marketplace", "acme/x")
        (self.t / ".claude/settings.json").write_text("{}")
        _, out = ti.run("doctor", "--target", str(self.t))
        self.assertIn("plugins not enabled for the project: guard, workflow", out)


if __name__ == "__main__":
    unittest.main()
