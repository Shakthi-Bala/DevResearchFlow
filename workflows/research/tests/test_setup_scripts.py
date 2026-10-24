"""Exercise setup behavior with fake CLIs: no downloads or real agent configuration."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


class SetupScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "project with spaces"
        self.project.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()
        self.mock = self.root / "mock-bin"
        self.mock.mkdir()
        self.log = self.root / "commands.log"
        self.graphify = self.root / "graphify-stub"
        self.graphify.write_text(
            '#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "$SETUP_TEST_LOG"\nif [ "$1" = --version ]; then echo "graphify 0.9.95"; fi\n'
        )
        self.graphify.chmod(0o755)
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "PATH": str(self.mock) + os.pathsep + "/usr/bin:/bin",
            "SETUP_TEST_LOG": str(self.log),
            "SETUP_TEST_GRAPHIFY": str(self.graphify),
            "GRAPHIFY_VERSION": "0.9.95",
        }
        # Python is not necessarily in /usr/bin on every runner.
        python = shutil.which("python3")
        (self.mock / "python3").symlink_to(python)
        self.link_graphify()

    def link_graphify(self):
        shutil.copy2(self.graphify, self.mock / "graphify")

    def fake_uv(self):
        path = self.mock / "uv"
        path.write_text(
            '#!/usr/bin/env bash\nprintf "uv %s\\n" "$*" >> "$SETUP_TEST_LOG"\nmkdir -p "$HOME/.local/bin"\ncp "$SETUP_TEST_GRAPHIFY" "$HOME/.local/bin/graphify"\n'
        )
        path.chmod(0o755)

    def run_graphify(self, *args):
        return subprocess.run(
            ["bash", str(REPO / "bin/graphify-init"), str(self.project), *args],
            env=self.env,
            capture_output=True,
            text=True,
        )

    def commands(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_default_graph_setup_is_agent_neutral(self):
        result = self.run_graphify("--no-hooks")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("extract . --code-only", self.commands())
        self.assertIn("cluster-only . --no-label", self.commands())
        self.assertNotIn("install", self.commands())
        self.assertNotIn("claude install", self.commands())

    def test_runtime_integration_requires_explicit_flag(self):
        result = self.run_graphify("--claude", "--no-hooks")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("install", self.commands())
        self.assertIn("claude install", self.commands())

    def test_fallback_install_uses_pinned_version(self):
        (self.mock / "graphify").unlink()
        self.fake_uv()
        result = self.run_graphify("--no-hooks")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("uv tool install --upgrade graphifyy[mcp]==0.9.95", self.commands())

    def test_existing_ignores_survive_rerun(self):
        (self.project / ".graphifyignore").write_text("custom-data/\n")
        self.assertEqual(self.run_graphify("--no-hooks").returncode, 0)
        self.assertEqual(self.run_graphify("--no-hooks").returncode, 0)
        self.assertEqual((self.project / ".graphifyignore").read_text(), "custom-data/\n")
        self.assertEqual(
            (self.project / ".gitignore").read_text().splitlines().count("graphify-out/"), 1
        )

    def test_commit_graph_removes_exact_ignore_entry(self):
        (self.project / ".gitignore").write_text("data/\ngraphify-out/\n")
        result = self.run_graphify("--commit-graph", "--no-hooks")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.project / ".gitignore").read_text(), "data/\n")

    def test_ignore_symlink_is_not_followed(self):
        outside = self.root / "outside"
        outside.write_text("preserve\n")
        (self.project / ".gitignore").symlink_to(outside)
        result = self.run_graphify("--no-hooks")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(outside.read_text(), "preserve\n")

    def test_unknown_options_do_not_run_commands(self):
        result = self.run_graphify("--invalid")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.commands(), [])

    def test_installer_skips_directories_and_default_agent_integration(self):
        self.fake_uv()
        source = self.root / "toolkit"
        (source / "bin/__pycache__").mkdir(parents=True)
        shutil.copy2(REPO / "install.sh", source / "install.sh")
        (source / "bin/research-init").write_text("#!/usr/bin/env python3\n")
        result = subprocess.run(
            ["bash", str(source / "install.sh")], env=self.env, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.home / ".local/bin/research-init").is_symlink())
        self.assertFalse((self.home / ".local/bin/__pycache__").exists())
        self.assertNotIn("install", self.commands())
        self.assertIn("uv tool install --upgrade graphifyy[mcp]==0.9.95", self.commands())


if __name__ == "__main__":
    unittest.main()
