import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("eng_ai", KIT / "installer" / "eng_ai.py")
eng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eng)


def run(*args, which="/usr/bin/tool"):
    """Run the CLI with every tool on PATH unless a test says otherwise (gitleaks is a sync warning)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), mock.patch.object(eng.shutil, "which", return_value=which):
        code = eng.main(list(args))
    return code, out.getvalue()


class TargetRepo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.t = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q", str(self.t)], check=True)

    def write(self, rel, text):
        path = self.t / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        subprocess.run(["git", "-C", str(self.t), "add", rel], check=True)

    def bootstrap(self, *extra):
        return run("bootstrap", "--target", str(self.t), *extra)


class BootstrapTest(TargetRepo):
    def test_dry_run_writes_nothing(self):
        code, out = self.bootstrap()
        self.assertEqual(code, 0)
        self.assertIn("dry run", out)
        self.assertFalse((self.t / "AGENTS.md").exists())
        self.assertFalse((self.t / ".eng-ai.json").exists())

    def test_apply_creates_kit_and_is_idempotent(self):
        self.write("a.py", "x = 1\n")
        self.write("pyproject.toml", "[tool.ruff]\n")  # so verify.sh detects a step
        self.bootstrap("--apply")
        for rel in ("AGENTS.md", "CLAUDE.md", ".eng-ai.json", "scripts/verify.sh", ".githooks/commit-msg",
                    ".githooks/pre-commit", ".githooks/pre-push", ".github/pull_request_template.md"):
            self.assertTrue((self.t / rel).is_file(), rel)
        self.assertTrue(os.access(self.t / "scripts/verify.sh", os.X_OK))
        self.assertEqual((self.t / "CLAUDE.md").read_text(), "@AGENTS.md\n")
        self.assertNotIn("languages", eng.read_config(self.t))
        self.assertEqual(eng.hooks_path(self.t), ".githooks")
        before = (self.t / "AGENTS.md").read_text()
        code, out = self.bootstrap("--apply")
        self.assertEqual((self.t / "AGENTS.md").read_text(), before)
        self.assertNotIn("create", out)
        self.assertNotIn("needs a human", out)
        self.assertEqual(code, 0)
        self.assertIn(f"next: python3 {KIT / 'installer/eng_ai.py'} doctor", out)

    def test_missing_gitleaks_and_undetected_verify_need_a_human(self):
        code, out = run("bootstrap", "--target", str(self.t), "--apply", which=None)
        self.assertEqual(code, 1)
        self.assertIn("needs a human: gitleaks is not on PATH; every commit will be blocked until you install it "
                      "(brew install gitleaks (https://github.com/gitleaks/gitleaks#installing))", out)
        self.assertIn("needs a human: verify.sh detects no checks", out)

    def test_deleted_managed_file_is_not_recreated(self):
        self.bootstrap("--apply")
        (self.t / ".githooks/pre-push").unlink()
        code, out = run("update", "--target", str(self.t), "--apply")
        self.assertEqual(code, 1)
        self.assertIn("needs a human: .githooks/pre-push was removed locally; delete its entry from 'managed'", out)
        self.assertFalse((self.t / ".githooks/pre-push").exists())
        self.assertIn(".githooks/pre-push", eng.read_config(self.t)["managed"])

    def test_existing_agents_md_is_kept_and_block_appended(self):
        self.write("AGENTS.md", "# Mine\n\nKeep this.\n")
        self.bootstrap("--apply")
        text = (self.t / "AGENTS.md").read_text()
        self.assertTrue(text.startswith("# Mine\n\nKeep this."))
        self.assertIn(eng.BLOCK_START, text)
        self.assertIn("- SEC-001 [enforced]", text)

    def test_existing_claude_md_is_flagged_not_edited(self):
        self.write("CLAUDE.md", "my rules\n")
        _, out = self.bootstrap("--apply")
        self.assertEqual((self.t / "CLAUDE.md").read_text(), "my rules\n")
        self.assertIn("does not import AGENTS.md", out)

    def test_existing_hook_and_hooks_path_are_flagged(self):
        self.write(".githooks/pre-commit", "#!/bin/sh\necho mine\n")
        subprocess.run(["git", "-C", str(self.t), "config", "core.hooksPath", ".husky"], check=True)
        _, out = self.bootstrap("--apply")
        self.assertEqual((self.t / ".githooks/pre-commit").read_text(), "#!/bin/sh\necho mine\n")
        self.assertIn(".githooks/pre-commit differs", out)
        self.assertIn("core.hooksPath is '.husky'", out)
        self.assertEqual(eng.hooks_path(self.t), ".husky")

    def test_not_a_git_repo_exits(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaises(SystemExit):
            run("bootstrap", "--target", d)

    def test_language_detection(self):
        self.write("a.kt", "")
        self.write("web/tsconfig.json", "{}")
        self.write("svc/app.py", "")
        self.bootstrap("--apply")
        self.assertEqual(eng.config_languages(eng.read_config(self.t), eng.git_files(self.t)),
                         ["kotlin", "python", "typescript"])

    def test_languages_are_redetected_on_update(self):
        self.write("a.py", "")
        self.bootstrap("--apply")
        self.assertFalse((self.t / ".eng-ai/lint/typescript").exists())
        self.write("tsconfig.json", "{}")
        run("update", "--target", str(self.t), "--apply")
        self.assertTrue((self.t / ".eng-ai/lint/typescript/eslint.config.mjs").is_file())


class UpdateTest(TargetRepo):
    def test_update_requires_config(self):
        with self.assertRaises(SystemExit):
            run("update", "--target", str(self.t))

    def test_update_refreshes_untouched_and_skips_modified(self):
        self.bootstrap("--apply")
        cfg = eng.read_config(self.t)
        # simulate an older kit: recorded hash matches the current (old) file content
        old = "#!/usr/bin/env bash\necho old\n"
        (self.t / ".githooks/pre-push").write_text(old)
        cfg["managed"][".githooks/pre-push"] = eng.sha(old.encode())
        (self.t / "scripts/verify.sh").write_text("# locally edited\n")
        eng.write_config(self.t, cfg)

        _, out = run("update", "--target", str(self.t), "--apply")
        self.assertEqual((self.t / ".githooks/pre-push").read_bytes(), (KIT / ".githooks/pre-push").read_bytes())
        self.assertEqual((self.t / "scripts/verify.sh").read_text(), "# locally edited\n")
        self.assertIn("update  .githooks/pre-push", out)
        self.assertIn("scripts/verify.sh differs", out)

    def test_update_preserves_user_config_keys(self):
        self.bootstrap("--apply")
        cfg = eng.read_config(self.t)
        cfg["verify"] = ["make test"]
        cfg["disabled"] = ["COD-004"]
        eng.write_config(self.t, cfg)
        run("update", "--target", str(self.t), "--apply")
        again = eng.read_config(self.t)
        self.assertEqual(again["verify"], ["make test"])
        self.assertEqual(again["disabled"], ["COD-004"])

    def test_stale_block_is_replaced(self):
        self.bootstrap("--apply")
        agents = self.t / "AGENTS.md"
        agents.write_text(agents.read_text().replace("Run `scripts/verify.sh`", "Run something else"))
        _, out = run("update", "--target", str(self.t), "--apply")
        self.assertIn("update  AGENTS.md managed block", out)
        self.assertIn("Run `scripts/verify.sh`", agents.read_text())


class DoctorTest(TargetRepo):
    def test_fresh_bootstrap_has_no_failures(self):
        self.bootstrap("--apply")
        with mock.patch.object(eng.shutil, "which", return_value="/usr/bin/tool"):
            code, out = run("doctor", "--target", str(self.t))
        self.assertEqual(code, 0, out)
        self.assertIn("always-loaded footprint", out)

    def test_missing_gitleaks_fails_with_install_hint(self):
        self.bootstrap("--apply")
        code, out = run("doctor", "--target", str(self.t), which=None)
        self.assertEqual(code, 1)
        self.assertIn("FAIL  gitleaks not on PATH; install: brew install gitleaks", out)

    def test_empty_repo_fails(self):
        code, out = run("doctor", "--target", str(self.t))
        self.assertEqual(code, 1)
        self.assertIn("FAIL  .eng-ai.json missing", out)

    def test_other_hooks_path_is_ok_when_it_delegates_else_warns(self):
        self.bootstrap("--apply")
        subprocess.run(["git", "-C", str(self.t), "config", "core.hooksPath", ".husky"], check=True)
        for hook in eng.KIT_HOOKS:
            self.write(f".husky/{hook}", f"#!/bin/sh\n.githooks/{hook} \"$@\"\n")
        code, out = run("doctor", "--target", str(self.t))
        self.assertEqual(code, 0, out)
        self.assertIn("OK    core.hooksPath is '.husky' and delegates to .githooks", out)
        (self.t / ".husky/pre-push").write_text("#!/bin/sh\necho mine\n")
        code, out = run("doctor", "--target", str(self.t))
        self.assertEqual(code, 0, out)
        self.assertIn("WARN  core.hooksPath is '.husky', not .githooks; call the kit hooks from it", out)

    def test_flags_claude_md_conflict_and_disabled(self):
        self.bootstrap("--apply")
        (self.t / "CLAUDE.md").write_text("own\n")
        cfg = eng.read_config(self.t)
        cfg["disabled"] = ["COD-004"]
        eng.write_config(self.t, cfg)
        code, out = run("doctor", "--target", str(self.t))
        self.assertEqual(code, 1)
        self.assertIn("CLAUDE.md does not import AGENTS.md", out)
        self.assertIn("WARN  disabled: COD-004", out)


class WorkflowTest(TargetRepo):
    def test_bootstrap_installs_security_workflow(self):
        self.bootstrap("--apply")
        self.assertTrue((self.t / ".github/workflows/eng-ai-security.yml").is_file())

    def test_every_action_is_pinned_to_a_commit(self):
        files = list(KIT.glob(".github/workflows/*.yml"))
        self.assertTrue(files)
        for path in files:
            for ref in re.findall(r"uses:\s*(\S+)", path.read_text()):
                self.assertRegex(ref, r"@[0-9a-f]{40}$", f"{path.name}: {ref} is not pinned to a SHA")

    def test_enforce_list_snippet(self):
        """The workflow's snippet reads only known checks from the "enforce" list."""
        wf = (KIT / ".github/workflows/eng-ai-security.yml").read_text()
        snippet = re.search(r"python3 -I -c '(.+?)' >>", wf).group(1)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".eng-ai.json").write_text(json.dumps({"verify": ["osv"], "enforce": ["semgrep", "trivy", "x"]}))
            out = subprocess.run(["python3", "-I", "-c", snippet], cwd=d, capture_output=True, text=True).stdout
        self.assertEqual(out.split(), ["semgrep=true", "trivy=true"])


class UninstallTest(TargetRepo):
    def test_dry_run_then_apply_removes_only_what_bootstrap_added(self):
        self.write("AGENTS.md", "# AGENTS.md\n\nOur own rule.\n")
        self.write("a.py", "")
        self.bootstrap("--apply", "--marketplace", "acme/eng-ai-standards")
        (self.t / ".githooks/pre-push").write_text("#!/bin/sh\necho mine\n")
        code, out = run("uninstall", "--target", str(self.t))
        self.assertEqual(code, 1)
        self.assertIn("would do", out)
        self.assertTrue((self.t / "scripts/verify.sh").is_file())
        code, out = run("uninstall", "--apply", "--target", str(self.t))
        self.assertEqual(code, 1)
        self.assertIn("needs a human: .githooks/pre-push was changed locally; left in place", out)
        for gone in ("scripts/verify.sh", ".githooks/pre-commit", ".eng-ai.json", "CLAUDE.md",
                     ".eng-ai/lint/python/ruff.toml", ".github/workflows/eng-ai-security.yml"):
            self.assertFalse((self.t / gone).exists(), gone)
        self.assertTrue((self.t / ".githooks/pre-push").is_file())
        self.assertEqual((self.t / "AGENTS.md").read_text(), "# AGENTS.md\n\nOur own rule.\n")
        self.assertEqual(eng.hooks_path(self.t), "")
        settings = json.loads((self.t / ".claude/settings.json").read_text())
        self.assertNotIn("eng-ai-standards", settings.get("extraKnownMarketplaces", {}))
        self.assertNotIn("guard@eng-ai-standards", settings.get("enabledPlugins", {}))

    def test_generated_agents_md_is_removed_entirely(self):
        self.write("a.py", "")
        self.bootstrap("--apply")
        run("uninstall", "--apply", "--target", str(self.t))
        self.assertFalse((self.t / "AGENTS.md").exists())

    def test_without_config_exits(self):
        with self.assertRaises(SystemExit):
            run("uninstall", "--target", str(self.t))


class ConfigValidationTest(TargetRepo):
    def test_rejects_unknown_key_wrong_type_bad_date_and_bad_json(self):
        bad_date = {"rule": "SEC-003", "owner": "@a", "reason": "r"}
        for text, msg in [('{"verfy": []}', "unknown key 'verfy'"), ('{"verify": "npm test"}', "'verify' must be a list"),
                          ('{"exceptions": [{"rule": "SEC-005"}]}', "each exception needs"), ("verify:\n  - x", "not valid JSON"),
                          (json.dumps({"exceptions": [{**bad_date, "expires": "never"}]}), "'never' is not a YYYY-MM-DD"),
                          (json.dumps({"exceptions": [{**bad_date, "expires": "2026-02-30"}]}), "'2026-02-30' is not")]:
            self.write(".eng-ai.json", text)
            with self.assertRaises(SystemExit) as ctx:
                eng.read_config(self.t)
            self.assertIn(msg, str(ctx.exception))


class DisabledRulesTest(TargetRepo):
    def config(self, **extra):
        self.bootstrap("--apply")
        cfg = eng.read_config(self.t)
        cfg.update(extra)
        eng.write_config(self.t, cfg)

    def test_disabled_rule_leaves_index_and_its_semgrep_pack(self):
        self.config()
        pack = self.t / ".eng-ai/lint/semgrep/ERR-001-swallowed-errors.yml"
        self.assertTrue(pack.is_file())
        cfg = eng.read_config(self.t)
        cfg["disabled"] = ["ERR-001", "SEC-004"]
        eng.write_config(self.t, cfg)
        _, out = run("update", "--apply", "--target", str(self.t))
        self.assertIn("remove  .eng-ai/lint/semgrep/ERR-001-swallowed-errors.yml", out)
        self.assertFalse(pack.exists())
        self.assertTrue((self.t / ".eng-ai/lint/semgrep/SEC-004-injection.yml").is_file())
        agents = (self.t / "AGENTS.md").read_text()
        self.assertNotIn("- ERR-001 [", agents)
        self.assertIn("- SEC-004 [", agents)
        self.assertIn("Disabled in this repo (do not apply): ERR-001", agents)

    def test_security_rule_cannot_be_disabled_and_expired_exception_fails(self):
        self.config(disabled=["SEC-005"], exceptions=[
            {"rule": "SEC-003", "owner": "@a", "expires": "2000-01-01", "reason": "legacy admin API"}])
        with mock.patch.object(eng.shutil, "which", return_value="/usr/bin/tool"):
            code, out = run("doctor", "--target", str(self.t))
        self.assertEqual(code, 1)
        self.assertIn("FAIL  SEC-005 cannot be disabled", out)
        self.assertIn("FAIL  exception to SEC-003 (owner @a) expired on 2000-01-01", out)

    def test_commit_msg_hook_respects_disabled_git_001(self):
        self.config(disabled=["GIT-001"])
        msg = self.t / "MSG"
        msg.write_text("whatever\n")
        r = subprocess.run([str(self.t / ".githooks/commit-msg"), str(msg)], cwd=self.t, capture_output=True)
        self.assertEqual(r.returncode, 0)

    def test_commit_msg_hook_limits_whole_subject_and_exempts_fixups(self):
        self.config()
        msg = self.t / "MSG"
        for subject, code, err in [("fix: " + "x" * 67, 0, ""), ("fix: " + "x" * 68, 1, "subject is 73 chars; max 72"),
                                   ("fixup! anything", 0, ""), ("squash! anything", 0, ""), ("bad subject", 1, "must match")]:
            msg.write_text(subject + "\n")
            r = subprocess.run([str(self.t / ".githooks/commit-msg"), str(msg)], cwd=self.t, capture_output=True, text=True)
            self.assertEqual(r.returncode, code, (subject, r.stderr))
            self.assertIn(err, r.stderr)


class VerifyScriptTest(unittest.TestCase):
    def verify(self, files, env=None):
        with tempfile.TemporaryDirectory() as d:
            for rel, text in files.items():
                (Path(d) / rel).parent.mkdir(parents=True, exist_ok=True)
                (Path(d) / rel).write_text(text)
            return subprocess.run([str(KIT / "scripts/verify.sh")], cwd=d, capture_output=True, text=True,
                                  env={**os.environ, **(env or {})})

    def test_override_pass_and_fail(self):
        ok = self.verify({".eng-ai.json": json.dumps({"verify": ["true", "echo hi"]})})
        self.assertEqual(ok.returncode, 0)
        self.assertIn("verify: PASS - 2 steps", ok.stdout)
        bad = self.verify({".eng-ai.json": json.dumps({"verify": ["true", "echo boom; false"]})})
        self.assertEqual(bad.returncode, 1)
        self.assertIn("FAIL  echo boom; false", bad.stdout)
        self.assertIn("boom", bad.stdout)
        self.assertIn("verify: FAIL - 2 steps, 1 failed", bad.stdout)

    def test_quoted_arguments_run_as_one_command(self):
        r = self.verify({".eng-ai.json": json.dumps({"verify": ['test "a b" = "a b"']})})
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_invalid_json_fails(self):
        r = self.verify({".eng-ai.json": "verify:\n  - true\n"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("not valid JSON", r.stderr)

    def test_node_detection(self):
        pkg = '{"scripts": {"lint": "x", "test": "y", "build": "z"}}'
        r = self.verify({"package.json": pkg, "pnpm-lock.yaml": ""}, {"VERIFY_LIST": "1"})
        self.assertEqual(r.stdout.split("\n")[:-1], ["pnpm run lint", "pnpm run test", "pnpm run build"])

    def test_python_detection(self):
        r = self.verify({"pyproject.toml": "[tool.ruff]\n[tool.mypy]\n"}, {"VERIFY_LIST": "1"})
        self.assertEqual(r.stdout.split("\n")[:-1], ["ruff check .", "mypy ."])

    def test_nothing_detected_fails_loudly(self):
        r = self.verify({"README.md": ""})
        self.assertEqual(r.returncode, 1)
        self.assertIn("no checks detected", r.stderr)

    def test_failing_pipeline_step_fails(self):
        r = self.verify({".eng-ai.json": json.dumps({"verify": ["false | true"]})})
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL  false | true", r.stdout)

    def test_nested_projects_refuse_auto_detection(self):
        r = self.verify({"pyproject.toml": "[tool.ruff]\n", "svc/api/package.json": "{}"}, {"VERIFY_LIST": "1"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("verify: nested projects found (svc/api/package.json); add a 'verify' list", r.stderr)

    def test_ruff_dotfile_and_setup_cfg_mypy_detected(self):
        r = self.verify({"requirements.txt": "", ".ruff.toml": "", "setup.cfg": "[mypy]\n"}, {"VERIFY_LIST": "1"})
        self.assertEqual(r.stdout.split("\n")[:-1], ["ruff check .", "mypy ."])

    def test_unittest_when_pytest_absent(self):
        r = self.verify({"requirements.txt": "", "tests/__init__.py": ""}, {"VERIFY_LIST": "1", "PATH": "/usr/bin:/bin"})
        self.assertEqual(r.stdout.split("\n")[:-1], ["python3 -m unittest discover -s tests"])

    def test_non_executable_gradlew_detected(self):
        r = self.verify({"gradlew": "#!/bin/sh\n"}, {"VERIFY_LIST": "1"})
        self.assertEqual(r.stdout.split("\n")[:-1], ["sh ./gradlew -q check"])


if __name__ == "__main__":
    unittest.main()
