"""Small stable CLI over the same versioned tools copied into each project."""

from __future__ import annotations

import argparse
import subprocess
import sys
from importlib.resources import files
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    try:
        toolkit = Path(str(files("devresearchflow.toolkit")))
    except ModuleNotFoundError as exc:
        # A source checkout exposes src/ directly without setuptools' package mapping.
        toolkit = Path(__file__).resolve().parents[2] / "workflows/research"
        if exc.name != "devresearchflow.toolkit" or not (toolkit / "VERSION").is_file():
            raise
    parser = argparse.ArgumentParser(prog="drf", description="DevResearchFlow research toolkit")
    parser.add_argument(
        "--version", action="version", version=(toolkit / "VERSION").read_text().strip()
    )
    parser.add_argument("--project", default=".", help="project root (before the command)")
    parser.add_argument(
        "command",
        choices=[
            "init",
            "new",
            "review",
            "pin",
            "advance",
            "prepare-run",
            "run",
            "execute",
            "check",
            "status",
            "artifact",
            "dataset-manifest",
            "migrate",
            "permissions",
        ],
    )
    raw = list(sys.argv[1:] if argv is None else argv)
    index = 0
    while index < len(raw):
        if raw[index] == "--project":
            index += 2
        elif raw[index].startswith("--project="):
            index += 1
        elif raw[index] in ("--help", "-h", "--version"):
            parser.parse_args(raw[: index + 1])
        else:
            break
    args = parser.parse_args(raw[: index + 1])
    remainder = raw[index + 1 :]
    root = Path(args.project).expanduser().resolve()
    if args.command == "init":
        command = [sys.executable, str(toolkit / "initialize.py")]
        if not any(not value.startswith("-") for value in remainder):
            command.append(str(root))
        command.extend(remainder)
    else:
        # Existing projects use their installed, versioned checker implementation.
        checks = root / ".research-toolkit/checks"
        if not checks.is_dir():
            parser.error("project is not initialized; run drf init first")
        if args.command == "check":
            script = (
                "validate_snapshot.py"
                if "--staged" in remainder or "--commit" in remainder
                else "validate_records.py"
            )
            command = [sys.executable, str(checks / script), str(root), *remainder]
        elif args.command in ("run", "execute", "status", "migrate", "permissions"):
            script = {
                "run": "execute.py",
                "execute": "execute.py",
                "status": "status.py",
                "migrate": "migrate.py",
                "permissions": "role_permissions.py",
            }[args.command]
            command = [sys.executable, str(checks / script), "--project", str(root), *remainder]
        else:
            command = [
                sys.executable,
                str(checks / "record_helper.py"),
                "--project",
                str(root),
                args.command,
                *remainder,
            ]
    try:
        return subprocess.call(command)
    except OSError as exc:
        print(f"drf: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
