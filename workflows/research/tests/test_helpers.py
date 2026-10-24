"""Exercise helpers and exact staged-tree validation through installed commands."""

import subprocess
import sys
from pathlib import Path

from test_toolkit import ToolkitFixture


class HelperTests(ToolkitFixture):
    def helper(self, *args):
        return subprocess.run(
            [
                sys.executable,
                str(self.root / ".research-toolkit/checks/record_helper.py"),
                "--project",
                str(self.root),
                *args,
            ],
            capture_output=True,
            text=True,
        )

    def test_create_and_review_remain_drafts(self):
        self.save(self.experiment())
        result = self.helper(
            "review", "REV-001", "--type", "protocol", "research/experiments/EXP-001.yaml"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        from records import content_hash, parse

        review = parse((self.root / "research/reviews/REV-001.yaml").read_text())
        self.assertEqual(review["status"], "draft")
        self.assertEqual(review["disposition"], "pending")
        experiment = parse((self.root / "research/experiments/EXP-001.yaml").read_text())
        self.assertEqual(
            review["target_versions"], {"EXP-001": content_hash(experiment, "protocol")}
        )
        self.assertNotEqual(
            self.helper(
                "review", "REV-001", "--type", "protocol", "research/experiments/EXP-001.yaml"
            ).returncode,
            0,
        )
        self.assertNotEqual(self.helper("new", "claim", "../../outside").returncode, 0)
        self.assertFalse((self.root / "outside").exists())

    def test_helper_preserves_existing_ids_and_symlink_targets(self):
        result = self.helper("new", "question", "Q-001")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.root / "research/questions/Q-001.md").exists())
        self.assertFalse((self.root / "research/questions/Q-001.yaml").exists())
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (self.root / "research/claims").rmdir()
        (self.root / "research/claims").symlink_to(outside, target_is_directory=True)
        self.assertNotEqual(self.helper("new", "claim", "CLM-001").returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_pin_rejects_uncommitted_code(self):
        self.ready_experiment()
        from records import parse

        path = self.root / "research/experiments/EXP-001.yaml"
        experiment = parse(path.read_text())
        experiment["status"] = "draft"
        self.save(experiment)
        result = self.helper("pin", "research/experiments/EXP-001.yaml")
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.root / "src/model.py").write_text("changed implementation\n")
        result = self.helper("pin", "research/experiments/EXP-001.yaml")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("commit implementation", result.stderr)

    def test_prepare_run_captures_provenance_without_execution(self):
        self.ready_experiment()
        (self.root / "environment.txt").write_text("fixture environment\n")
        (self.root / "dataset.json").write_text('{"fixture":true}\n')
        args = (
            "prepare-run",
            "RUN-001",
            "research/experiments/EXP-001.yaml",
            "--environment",
            "environment.txt",
            "--dataset-version",
            "fixture-v1",
            "--dataset-manifest",
            "dataset.json",
            "--device",
            "CPU",
            "--seed",
            "1",
            "--exec",
            "python3",
            "src/model.py",
        )
        result = self.helper(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        from records import parse, sha256

        manifest = parse((self.root / "runs/RUN-001/manifest.yaml").read_text())
        self.assertEqual(manifest["status"], "planned")
        self.assertIsNone(manifest["started_at"])
        self.assertEqual(
            manifest["protocol_snapshot"]["sha256"],
            sha256(self.root / "runs/RUN-001/protocol.yaml"),
        )
        self.assertFalse((self.root / "runs/RUN-001/stdout.log").exists())
        self.assertEqual(self.errors(), [])
        self.assertNotEqual(self.helper(*args).returncode, 0)

    def test_snapshot_uses_staged_files_and_ignores_working_repairs(self):
        self.git("init", "-q")
        self.init("--hooks", "--ci")
        self.git("add", ".")
        self.assertEqual(self.snapshot().returncode, 0, self.snapshot().stdout)
        self.git(
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "initial",
        )
        state = self.root / "research/state.yaml"
        original = state.read_text()
        state.write_text("bad: [")
        self.git("add", "research/state.yaml")
        state.write_text(original)
        result = self.snapshot()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("invalid YAML", result.stdout)
        self.git("add", "research/state.yaml")
        state.write_text("bad: [")
        self.assertEqual(self.snapshot().returncode, 0)
        self.assertTrue((self.root / ".git/hooks/pre-commit").is_file())
        self.assertTrue((self.root / ".github/workflows/research-records.yml").is_file())
        hook = self.root / ".git/hooks/pre-commit"
        hook.write_text("# custom\n")
        self.init("--hooks")
        self.assertEqual(hook.read_text(), "# custom\n")

    def test_snapshot_detects_terminal_manifest_deletion(self):
        run = self.run_record()
        run.update(
            status="failed",
            finished_at="2026-10-24T12:01:00Z",
            exit_code=1,
            failure_reason="fixture",
        )
        self.save(run)
        self.git("add", ".")
        self.git(
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "failed fixture",
        )
        self.git("rm", "runs/RUN-001/manifest.yaml")
        result = self.snapshot()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("deleted", result.stdout)

    def test_commit_snapshot_checks_parent_transition(self):
        e = self.experiment()
        self.save(e)
        self.git("init", "-q")
        self.git("add", ".")
        self.git(
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "draft",
        )
        e["status"] = "completed"
        self.save(e)
        self.git("add", ".")
        self.git(
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "skip gates",
        )
        result = self.snapshot("--commit", "HEAD")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden transition", result.stdout)

    def test_actual_hook_rejects_invalid_index(self):
        self.git("init", "-q")
        self.init("--hooks")
        state = self.root / "research/state.yaml"
        original = state.read_text()
        state.write_text("bad: [")
        self.git("add", ".")
        state.write_text(original)
        result = subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-qm",
                "invalid staged record",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid YAML", result.stdout + result.stderr)

    def test_staged_artifact_corruption_cannot_be_hidden(self):
        run = self.run_record()
        run.update(
            status="failed",
            finished_at="2026-10-24T12:01:00Z",
            exit_code=1,
            failure_reason="fixture",
        )
        self.save(run)
        self.git("add", ".")
        self.git(
            "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "run"
        )
        environment = self.root / "runs/RUN-001/environment.txt"
        original = environment.read_bytes()
        environment.write_text("corrupted staged evidence")
        self.git("add", "runs/RUN-001/environment.txt")
        environment.write_bytes(original)
        result = self.snapshot()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checksum mismatch", result.stdout)

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args], check=True, capture_output=True, text=True
        )

    def snapshot(self, *args):
        return subprocess.run(
            [
                sys.executable,
                str(self.root / ".research-toolkit/checks/validate_snapshot.py"),
                str(self.root),
                *(args or ("--staged",)),
            ],
            capture_output=True,
            text=True,
        )
