#!/usr/bin/env python3
"""Generate opt-in runtime role profiles; never overwrite user/runtime settings."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

from record_helper import output

AREAS = {
    "coordinator": [
        "research/brief.md",
        "research/state.yaml",
        "research/questions/",
        "research/tasks/",
        "research/decisions/",
        "research/claims/",
    ],
    "literature": ["research/sources/"],
    "hypothesis": ["research/hypotheses/"],
    "methodology": ["research/experiments/"],
    "engineer": ["src/", "configs/", "scripts/", "runs/", "tests/implementation/"],
    "verifier": ["research/reviews/", "tests/verification/"],
    "analyst": ["analysis/", "research/observations/"],
}
READ_TOOLS = {
    "Read",
    "Glob",
    "Grep",
    "LS",
    "WebSearch",
    "WebFetch",
    "AskUserQuestion",
    "TodoWrite",
    "TaskCreate",
    "TaskUpdate",
    "TaskGet",
    "TaskList",
}


def allowed(root: Path, role: str, filename: str) -> bool:
    path = Path(filename)
    if not path.is_absolute():
        path = root / path
    try:
        relative = path.relative_to(root).as_posix()
        output(root, relative)  # Reject symlinks, including a yet-uncreated leaf.
    except (ValueError, OSError):
        return False
    return any(
        relative.startswith(area) if area.endswith("/") else relative == area
        for area in AREAS[role]
    )


def guard(root: Path, role: str) -> int:
    event = json.load(sys.stdin)
    tool = event.get("tool_name")
    if tool in READ_TOOLS:
        return 0
    if tool in {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
        values = event.get("tool_input", {})
        filename = values.get("file_path") or values.get("notebook_path")
        if isinstance(filename, str) and allowed(root, role, filename):
            return 0
    print(
        f"DRF {role}: denied {tool}; file writes must stay in assigned areas; shell, delegation and unknown tools are disabled",
        file=sys.stderr,
    )
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".")
    parser.add_argument("--runtime", choices=["codex", "claude"])
    parser.add_argument("--role", choices=AREAS)
    parser.add_argument("--output")
    parser.add_argument("--guard", choices=AREAS, help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = Path(args.project).resolve()
    if args.guard:
        return guard(root, args.guard)
    if not args.runtime or not args.role:
        parser.error("--runtime and --role are required")
    role = args.role
    if args.runtime == "codex":
        name = f"drf_{role}"
        lines = [
            "# Merge this fragment into a dedicated trusted Codex configuration.",
            "# Do not combine default_permissions with sandbox_mode/sandbox_workspace_write.",
            f'default_permissions = "{name}"',
            'approval_policy = "never"',
            "",
            f"[permissions.{name}]",
            'extends = ":read-only"',
            "",
            f"[permissions.{name}.filesystem]",
        ]
        for area in AREAS[role]:
            lines.append(f'{json.dumps(str(root / area))} = "write"')
        lines += ["", f"[permissions.{name}.network]", "enabled = false", ""]
        text = "\n".join(lines)
        suffix = "toml"
    else:
        script = Path(__file__).resolve()
        command = shlex.join([sys.executable, str(script), "--project", str(root), "--guard", role])
        permissions = {
            "defaultMode": "dontAsk",
            "deny": ["Bash", "PowerShell", "Agent", "mcp__*"],
            "allow": [
                f"Edit(//{str(root / area).lstrip('/')}{'**' if area.endswith('/') else ''})"
                for area in AREAS[role]
            ],
        }
        text = (
            json.dumps(
                {
                    "permissions": permissions,
                    "hooks": {
                        "PreToolUse": [
                            {"matcher": ".*", "hooks": [{"type": "command", "command": command}]}
                        ]
                    },
                },
                indent=2,
            )
            + "\n"
        )
        suffix = "json"
    path = output(
        root, args.output or f".research-toolkit/permissions/{role}.{args.runtime}.{suffix}"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(text)
    print(
        f"Generated {path}; review and activate in a separate runtime session. No runtime settings were changed."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError) as exc:
        raise SystemExit(f"drf permissions: {exc}")
