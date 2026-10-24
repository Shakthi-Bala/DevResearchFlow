#!/usr/bin/env python3
"""Generate lifecycle diagrams from the validator and schema enums."""

import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render() -> str:
    tree = ast.parse((ROOT / "workflows/research/checks/validate_records.py").read_text())
    transitions = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "TRANSITIONS" for t in node.targets)
    )
    parts = [
        "# Record transitions\n",
        "Generated from validator transitions and schema enums. Regenerate with "
        "`python scripts/render_record_states.py`; CI checks for drift.\n",
        "Commit gates as they occur. A valid runner receipt also permits a planned "
        "run to reach a terminal state in one Git commit because it records the actual start. "
        "Terminal manifests remain immutable.\n",
    ]
    for kind, edges in transitions.items():
        schema = json.loads((ROOT / f"workflows/research/schemas/{kind}.schema.json").read_text())
        parts += [f"## {kind.title()}\n", "```mermaid", "stateDiagram-v2"]
        for status in schema["properties"]["status"]["enum"]:
            parts.append(f'    state "{status}" as {status}')
        for before, after_values in edges.items():
            for after in sorted(after_values):
                parts.append(f"    {before} --> {after}")
        if kind == "run":
            parts += [
                "    planned --> completed: verified runner receipt",
                "    planned --> failed: verified runner receipt",
            ]
        parts += ["```", ""]
    parts += [
        "## Project state\n",
        "`research/state.yaml` is a pointer/status document rather than a lifecycle record. "
        "Its `phase` is free text; these links are type-checked.\n",
        "```mermaid",
        "flowchart LR",
        '    State --> active_question["active_question: Q or null"]',
        '    State --> active_tasks["active_tasks: TASK IDs"]',
        '    State --> current_experiment["current_experiment: EXP or null"]',
        '    State --> blockers["blockers and next_decision"]',
        "```",
        "",
    ]
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / "docs/record-states.md"
    text = render()
    if args.check:
        if not path.exists() or path.read_text() != text:
            print("Record diagrams are stale; run python scripts/render_record_states.py")
            return 1
        return 0
    path.write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
