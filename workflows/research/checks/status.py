#!/usr/bin/env python3
"""Show current gates, validation failures, and concrete next actions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_references import reference_errors
from provenance import policy
from records import load_records
from validate_records import policy_errors

ACTIONS = {
    "draft": "finish protocol, then drf review REV-NNN --type protocol <experiment>",
    "protocol_reviewed": "implement and pin code/config, then obtain implementation review",
    "implementation_reviewed": "drf prepare-run RUN-NNN <experiment> ... then drf run RUN-NNN",
    "executing": "drf run RUN-NNN for remaining planned runs; preserve failures",
    "completed": "analyze all runs and obtain independent evidence review",
    "superseded": "follow the replacement experiment",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.project).resolve()
    records, errors = load_records(root)
    errors += reference_errors(root, records) + policy_errors(root, records)
    experiments = [
        dict(id=r["id"], gate=r["status"], next_action=ACTIONS[r["status"]])
        for r, _ in records.values()
        if r["kind"] == "experiment"
    ]
    runs = [dict(id=r["id"], status=r["status"]) for r, _ in records.values() if r["kind"] == "run"]
    result = {
        "policy": policy(root),
        "experiments": experiments,
        "runs": runs,
        "errors": errors,
        "next_action": "repair listed validation errors first"
        if errors
        else (
            "follow the experiment actions"
            if experiments
            else "fill research/brief.md and the initial question"
        ),
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"DevResearchFlow: {len(records)} records, {len(errors)} blockers")
        for item in experiments:
            print(f"{item['id']}: {item['gate']} → {item['next_action']}")
        for item in runs:
            print(f"{item['id']}: {item['status']}")
        for error in errors:
            print(f"BLOCKED: {error}")
        print("Next: " + result["next_action"])
    return bool(errors)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError) as exc:
        raise SystemExit(f"drf status: {exc}")
