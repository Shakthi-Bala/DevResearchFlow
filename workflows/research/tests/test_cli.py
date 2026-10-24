"""Test installed CLI routing, migration safety, default hooks and role profiles."""

import json
import os
import subprocess
import sys
from pathlib import Path

from test_toolkit import ToolkitFixture


class CliTests(ToolkitFixture):
    def cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "devresearchflow", "--project", str(self.root), *args],
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")
                + os.pathsep
                + os.environ.get("PYTHONPATH", ""),
            },
        )

    def test_commands_and_subcommand_help(self):
        result = self.cli(
            "new", "claim", "CLM-001", "--model", "fixture-model", "--session", "fixture-session"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.cli("status", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["errors"], [])
        result = self.cli("run", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--timeout", result.stdout)
        result = self.cli("check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.cli("new", "claim", "CLM-001")
        self.assertNotEqual(result.returncode, 0)

    def test_new_projects_are_strict_and_install_hooks_by_default(self):
        root = Path(self.temp.name) / "new strict project"
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        result = self.cli("init", "--ci", str(root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((root / ".git/hooks/pre-commit").is_file())
        policy = json.loads((root / "research/policy.json").read_text())
        self.assertTrue(policy["execution_receipts"])
        self.assertTrue(policy["review_identity"])
        metadata = json.loads((root / "research/toolkit_version.json").read_text())
        self.assertEqual(metadata["toolkit_version"], "0.3.0")
        self.assertTrue((root / ".github/workflows/research-records.yml").exists())

    def test_missing_policy_cannot_silently_downgrade(self):
        (self.root / "research/policy.json").unlink()
        result = self.cli("check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("restore its committed policy", result.stdout + result.stderr)

    def test_metadata_migration_has_backup_and_is_idempotent(self):
        path = self.root / "research/toolkit_version.json"
        value = json.loads(path.read_text())
        value["format_version"] = 1
        value.pop("toolkit_version", None)
        path.write_text(json.dumps(value))
        before = path.read_bytes()
        result = self.cli("migrate", "--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(path.read_bytes(), before)
        result = self.cli("migrate")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(path.read_text())["format_version"], 2)
        backups = list((self.root / ".research-toolkit/migrations").glob("*/toolkit_version.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), before)
        updated = path.read_bytes()
        self.assertEqual(self.cli("migrate").returncode, 0)
        self.assertEqual(updated, path.read_bytes())
        self.assertFalse(
            json.loads((self.root / "research/policy.json").read_text())["execution_receipts"]
        )

    def test_migration_cannot_fabricate_historical_receipts(self):
        self.run_record()
        result = self.cli("migrate", "--strict")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot invent historical", result.stderr)
        self.assertFalse(
            json.loads((self.root / "research/policy.json").read_text())["execution_receipts"]
        )

    def test_permission_profiles_are_generated_without_overwriting(self):
        for runtime in ("codex", "claude"):
            result = self.cli("permissions", "--runtime", runtime, "--role", "verifier")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotEqual(
                self.cli("permissions", "--runtime", runtime, "--role", "verifier").returncode, 0
            )
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        config = tomllib.loads(
            (self.root / ".research-toolkit/permissions/verifier.codex.toml").read_text()
        )
        permissions = config["permissions"]["drf_verifier"]
        self.assertEqual(permissions["extends"], ":read-only")
        self.assertEqual(
            set(permissions["filesystem"]),
            {str(self.root / "research/reviews"), str(self.root / "tests/verification")},
        )
        config = json.loads(
            (self.root / ".research-toolkit/permissions/verifier.claude.json").read_text()
        )
        self.assertNotIn("Bash", config["permissions"]["deny"])
        self.assertEqual(
            len([v for v in config["permissions"]["allow"] if v.startswith("Bash(")]), 2
        )
        self.assertIn("mcp__*", config["permissions"]["deny"])
        self.assertTrue(config["hooks"]["PreToolUse"])
        self.assertFalse((self.root / ".claude/settings.json").exists())

    def test_superseding_a_review_preserves_markdown_narrative(self):
        self.save(self.experiment())
        review = self.template("review")
        review.update(
            status="completed", disposition="supported_within_scope", checks_performed=["fixture"]
        )
        from records import content_hash, yaml

        target = self.experiment()
        review["target_versions"] = {"EXP-001": content_hash(target, "protocol")}
        path = self.root / "research/reviews/REV-001.md"
        path.write_text(
            "---\n"
            + yaml.safe_dump(review, sort_keys=False)
            + "---\n\nOriginal reasoning retained.\n"
        )
        result = self.cli(
            "review",
            "REV-002",
            "--type",
            "protocol",
            "--supersedes",
            "REV-001",
            "research/experiments/EXP-001.yaml",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Original reasoning retained.", path.read_text())
        self.assertIn("status: superseded", path.read_text())
        self.assertIn(
            "disposition: pending", (self.root / "research/reviews/REV-002.yaml").read_text()
        )

    def test_generated_profiles_are_ignored_on_install_and_update(self):
        self.cli("permissions", "--runtime", "claude", "--role", "verifier")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        profile = ".research-toolkit/permissions/verifier.claude.json"
        result = subprocess.run(
            ["git", "-C", str(self.root), "check-ignore", profile], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        ignore = self.root / ".gitignore"
        ignore.write_text(ignore.read_text().replace(".research-toolkit/permissions/\n", ""))
        self.init("--update")
        result = subprocess.run(
            ["git", "-C", str(self.root), "check-ignore", profile], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
