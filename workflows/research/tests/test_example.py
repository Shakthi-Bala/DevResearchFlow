"""Keep the walkthrough executable, including every recorded workflow transition."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


class ExampleTests(unittest.TestCase):
    def test_complete_example_preserves_failures_and_contradiction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "example with spaces"
            result = subprocess.run(
                [sys.executable, str(REPO / "examples/toy-ablation/build.py"), str(root)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("All commit snapshots validated", result.stdout)
            metrics = json.loads((root / "runs/RUN-002/metrics.json").read_text())
            self.assertEqual(metrics, {"baseline_mse": 0.0, "ablated_mse": 7.5, "difference": 7.5})
            self.assertIn("status: failed", (root / "runs/RUN-001/manifest.yaml").read_text())
            self.assertIn(
                "Injected demonstration failure", (root / "runs/RUN-001/stderr.log").read_text()
            )
            self.assertIn(
                "status: contradicted", (root / "research/hypotheses/HYP-001.yaml").read_text()
            )
            self.assertIn("stale review", (root / "research/sessions/stale-review.txt").read_text())
            self.assertIn(
                "No independent reviewer", (root / "research/reviews/REV-004.yaml").read_text()
            )

            result = subprocess.run(
                [sys.executable, str(REPO / "bin/research-init"), str(root), "--hooks"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((root / "research/questions/Q-001.md").exists())
            check = subprocess.run(
                [
                    sys.executable,
                    str(root / ".research-toolkit/checks/validate_records.py"),
                    str(root),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

            status = subprocess.run(
                [
                    sys.executable,
                    str(root / ".research-toolkit/checks/status.py"),
                    "--project",
                    str(root),
                    "--json",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
            summary = json.loads(status.stdout)
            self.assertIn("DEC-001", summary["next_action"])
            self.assertNotIn("obtain independent evidence review", summary["next_action"])
