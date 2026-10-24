"""Exercise actual process execution, strict provenance and review boundaries."""

import json
import os
import signal
import subprocess
import sys
import time

from records import parse, sha256
from test_toolkit import ToolkitFixture


class ExecutionTests(ToolkitFixture):
    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    def commit(self):
        self.git("add", ".")
        self.git(
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "fixture gate",
        )

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

    def prepared(self, flags=(), confirmatory=False):
        e = self.experiment()
        e["author"] = {"role": "methodology", "model": "fixture-author", "session": "author-1"}
        e["implementation"]["author"] = {
            "role": "engineer",
            "model": "fixture-author",
            "session": "engineer-1",
        }
        if confirmatory:
            e["mode"] = "confirmatory"
        self.put("configs/model.yaml", {"width": 2})
        self.put("configs/data.yaml", {"x": [1, 2, 3]})
        (self.root / "configs/environment.txt").write_text(sys.version)
        (self.root / "src/model.py").write_text("""import argparse,json,os,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--fail',action='store_true');p.add_argument('--sleep',action='store_true');p.add_argument('--mutate',action='store_true');a=p.parse_args()
print('actual partial output',flush=True)
if a.sleep:time.sleep(20)
if a.fail:raise SystemExit('actual failure')
if a.mutate:Path('src/model.py').write_text('mutated')
(Path(os.environ['DRF_RUN_DIR'])/'metrics.json').write_text(json.dumps({'score':3}))
""")
        result = self.helper("dataset-manifest", "configs/data-manifest.json", "configs/data.yaml")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.save(e)
        self.git("init", "-q")
        self.commit()
        e["implementation"]["commit"] = self.git("rev-parse", "HEAD")
        e["configuration"]["sha256"] = sha256(self.root / "configs/model.yaml")
        for rid, stage in [("REV-001", "protocol"), ("REV-002", "implementation")]:
            r = self.review(rid, e, stage)
            r["reviewer"] = {"role": "verifier", "model": "fixture-reviewer", "session": rid}
            self.save(r)
        e["required_reviews"] = {"protocol": "REV-001", "implementation": "REV-002"}
        e["status"] = "implementation_reviewed"
        self.save(e)
        (self.root / "research/policy.json").write_text(
            json.dumps({"format_version": 2, "execution_receipts": True, "review_identity": True})
        )
        self.assertEqual(self.errors(), [])
        self.commit()
        result = self.helper(
            "prepare-run",
            "RUN-001",
            "research/experiments/EXP-001.yaml",
            "--environment",
            "configs/environment.txt",
            "--dataset-version",
            "fixture-v1",
            "--dataset-manifest",
            "configs/data-manifest.json",
            "--device",
            "CPU",
            "--exec",
            sys.executable,
            "src/model.py",
            *flags,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.commit()
        return e

    def runner(self, *args):
        return subprocess.run(
            [
                sys.executable,
                str(self.root / ".research-toolkit/checks/execute.py"),
                "--project",
                str(self.root),
                "RUN-001",
                *args,
            ],
            capture_output=True,
            text=True,
        )

    def manifest(self):
        return parse((self.root / "runs/RUN-001/manifest.yaml").read_text())

    def test_success_receipts_and_log_tampering(self):
        self.prepared()
        result = self.runner()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        r = self.manifest()
        self.assertEqual(r["status"], "completed")
        self.assertEqual(r["exit_code"], 0)
        self.assertEqual(json.loads((self.root / r["metrics"]["path"]).read_text()), {"score": 3})
        self.assertTrue(r["started_at"])
        self.assertTrue(r["finished_at"])
        self.assertEqual(self.errors(), [])
        from records import load_records
        from validate_records import history_errors

        records, _ = load_records(self.root)
        self.assertEqual(history_errors(self.root, records, "HEAD"), [])
        self.assertNotEqual(self.runner().returncode, 0)
        (self.root / r["logs"]["stdout"]).write_text("fabricated stdout")
        self.assertTrue(any("execution evidence changed" in error for error in self.errors()))

    def test_code_and_dataset_changes_refuse_before_launch(self):
        self.prepared()
        source = self.root / "src/model.py"
        original = source.read_text()
        source.write_text("changed")
        self.assertNotEqual(self.runner().returncode, 0)
        self.assertEqual(self.manifest()["status"], "planned")
        source.write_text(original)
        (self.root / "configs/data.yaml").write_text("different data")
        result = self.runner()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dataset files changed", result.stderr)
        self.assertFalse((self.root / "runs/RUN-001/stdout.log").exists())

    def test_failed_command_keeps_partial_evidence(self):
        self.prepared(("--fail",))
        result = self.runner()
        self.assertNotEqual(result.returncode, 0)
        r = self.manifest()
        self.assertEqual(r["status"], "failed")
        self.assertNotEqual(r["exit_code"], 0)
        self.assertIn("partial output", (self.root / r["logs"]["stdout"]).read_text())
        self.assertIn("actual failure", (self.root / r["logs"]["stderr"]).read_text())
        self.assertEqual(self.errors(), [])

    def test_timeout_is_recorded_without_losing_logs(self):
        self.prepared(("--sleep",))
        result = self.runner("--timeout", "0.2")
        self.assertNotEqual(result.returncode, 0)
        r = self.manifest()
        self.assertEqual(r["status"], "failed")
        self.assertIn("timeout", r["failure_reason"])
        self.assertTrue(r["execution"])
        self.assertEqual(self.errors(), [])

    def test_sigterm_preserves_cancelled_execution(self):
        if os.name != "posix":
            self.skipTest("POSIX signal test")
        self.prepared(("--sleep",))
        process = subprocess.Popen(
            [
                sys.executable,
                str(self.root / ".research-toolkit/checks/execute.py"),
                "--project",
                str(self.root),
                "RUN-001",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            deadline = time.monotonic() + 10
            log = self.root / "runs/RUN-001/stdout.log"
            while time.monotonic() < deadline:
                if log.exists() and "partial output" in log.read_text():
                    break
                if process.poll() is not None:
                    break
                time.sleep(0.05)
            self.assertTrue(log.exists() and "partial output" in log.read_text())
            process.send_signal(signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=10)
            self.assertNotEqual(process.returncode, 0, stdout + stderr)
            self.assertEqual(self.manifest()["status"], "cancelled")
            self.assertEqual(self.errors(), [])
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()

    def test_missing_receipts_and_self_review_are_rejected(self):
        self.prepared()
        self.assertEqual(self.runner().returncode, 0)
        r = self.manifest()
        r.pop("execution")
        self.save(r)
        self.assertTrue(any("execution receipt required" in e for e in self.errors()))
        path = self.root / "research/reviews/REV-001.yaml"
        review = parse(path.read_text())
        review["reviewer"]["session"] = "author-1"
        self.save(review)
        self.assertTrue(any("self-review session" in e for e in self.errors()))

    def test_confirmatory_registration_is_checked(self):
        self.prepared(confirmatory=True)
        result = self.runner()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        r = self.manifest()
        self.assertTrue(r["registration_commit"])
        self.assertEqual(self.errors(), [])
        r["registration_commit"] = None
        self.save(r)
        self.assertTrue(any("preregistration" in e for e in self.errors()))

    def test_implementation_reviewer_cannot_be_the_code_author(self):
        self.prepared()
        review = parse((self.root / "research/reviews/REV-002.yaml").read_text())
        review["reviewer"]["session"] = "engineer-1"
        self.save(review)
        self.assertTrue(
            any("self-review session for implementation" in error for error in self.errors())
        )

    def test_midrun_code_mutation_is_failed(self):
        self.prepared(("--mutate",))
        result = self.runner()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.manifest()["status"], "failed")
        self.assertIn("inputs changed", self.manifest()["failure_reason"])

    def test_role_guard_blocks_shell_and_outside_writes(self):
        script = self.root / ".research-toolkit/checks/role_permissions.py"
        for tool, filename, code in [
            ("Edit", "research/reviews/REV-009.md", 0),
            ("Write", "src/model.py", 2),
            ("Bash", None, 2),
            ("mcp__external__write", None, 2),
        ]:
            result = subprocess.run(
                [sys.executable, str(script), "--project", str(self.root), "--guard", "verifier"],
                input=json.dumps({"tool_name": tool, "tool_input": {"file_path": filename}}),
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, code, result.stderr)

    def test_dataset_addition_is_detected(self):
        (self.root / "data").mkdir()
        (self.root / "data/a.txt").write_text("a")
        result = self.helper("dataset-manifest", "configs/data-manifest.json", "data")
        self.assertEqual(result.returncode, 0, result.stderr)
        from provenance import verify_dataset

        dataset = {
            "manifest_path": "configs/data-manifest.json",
            "manifest_sha256": sha256(self.root / "configs/data-manifest.json"),
        }
        verify_dataset(self.root, dataset)
        (self.root / "data/b.txt").write_text("b")
        with self.assertRaisesRegex(ValueError, "added or removed"):
            verify_dataset(self.root, dataset)

    def test_environment_capture_is_automatic_and_receipt_covered(self):
        self.prepared()
        result = self.runner()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        path = self.root / "runs/RUN-001/environment-captured.json"
        captured = json.loads(path.read_text())
        self.assertEqual(captured["runner"]["executable"], sys.executable)
        self.assertTrue(captured["runner"]["packages"])
        command_python = json.loads(captured["command_python"]["stdout"])
        self.assertEqual(command_python["executable"], sys.executable)
        self.assertIn("CUDA_VISIBLE_DEVICES", captured["variables"])
        self.assertIn("gpu", captured)
        manifest = self.manifest()
        self.assertIn(
            "runs/RUN-001/environment-captured.json", [a["path"] for a in manifest["artifacts"]]
        )
        receipt = json.loads((self.root / manifest["execution"]["path"]).read_text())
        self.assertIn("runs/RUN-001/environment-captured.json", receipt["files"])
        path.write_text("fabricated environment")
        self.assertTrue(any("execution evidence changed" in e for e in self.errors()))

    def test_verifier_guard_allows_only_exact_verification_commands(self):
        script = self.root / ".research-toolkit/checks/role_permissions.py"
        profile = subprocess.run(
            [
                sys.executable,
                str(script),
                "--project",
                str(self.root),
                "--runtime",
                "claude",
                "--role",
                "verifier",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(profile.returncode, 0, profile.stderr)
        settings = json.loads(
            (self.root / ".research-toolkit/permissions/verifier.claude.json").read_text()
        )
        commands = [
            rule[5:-1] for rule in settings["permissions"]["allow"] if rule.startswith("Bash(")
        ]
        self.assertEqual(len(commands), 2)
        for command, expected in [(c, 0) for c in commands] + [
            (commands[0] + " && touch src/evil.py", 2),
            (commands[1] + " ../implementation", 2),
            ("python -c 'print(1)'", 2),
        ]:
            result = subprocess.run(
                [sys.executable, str(script), "--project", str(self.root), "--guard", "verifier"],
                input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, expected, result.stderr)
