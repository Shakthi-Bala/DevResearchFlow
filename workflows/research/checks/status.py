#!/usr/bin/env python3
"""Show current gates, validation failures, and concrete next actions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_references import reference_errors
from provenance import policy
from records import content_hash, load_records
from validate_records import policy_errors

ACTIONS = {
    "draft": "finish protocol, then drf review REV-NNN --type protocol <experiment>",
    "protocol_reviewed": "implement and pin code/config, then obtain implementation review",
    "implementation_reviewed": "drf prepare-run RUN-NNN <experiment> ... then drf run RUN-NNN",
    "executing": "drf run RUN-NNN for remaining planned runs; preserve failures",
    "completed": "analyze all runs and obtain independent evidence review",
    "superseded": "follow the replacement experiment",
}


def next_action(experiment, records):
    rid = experiment["id"]
    status = experiment["status"]
    if status == "executing":
        runs = [r for r, _ in records.values() if r["kind"] == "run" and r["experiment"] == rid]
        active = [r for r in runs if r["status"] == "started"]
        if active:
            return f"inspect running {active[0]['id']} logs; preserve partial evidence"
        planned = [r for r in runs if r["status"] == "planned"]
        if planned:
            return f"drf run {planned[0]['id']}"
        if runs:
            return f"drf advance {rid} completed; commit the gate"
    if status != "completed":
        if status == "implementation_reviewed":
            planned = [
                r
                for r, _ in records.values()
                if r["kind"] == "run" and r["experiment"] == rid and r["status"] == "planned"
            ]
            if planned:
                return f"drf run {planned[0]['id']}"
            finished = [
                r
                for r, _ in records.values()
                if r["kind"] == "run" and r["experiment"] == rid and r["started_at"]
            ]
            if finished:
                return f"drf advance {rid} executing; commit the gate"
        return ACTIONS[status]
    run_ids = {
        r["id"] for r, _ in records.values() if r["kind"] == "run" and r["experiment"] == rid
    }
    observations = [
        r for r, _ in records.values() if r["kind"] == "observation" and r["run"] in run_ids
    ]
    evidence = run_ids | {r["id"] for r in observations}
    claims = [
        r
        for r, _ in records.values()
        if r["kind"] == "claim"
        and evidence.intersection(r["supporting_evidence"] + r["contradicting_evidence"])
    ]
    if not observations:
        return f"analyze all runs for {rid} and create linked observations"
    if not claims:
        return f"create a claim linked to observations for {rid}"
    reviews = []
    for claim in claims:
        current = [
            r
            for r, _ in records.values()
            if r["kind"] == "review"
            and r["review_type"] == "evidence"
            and r["status"] == "completed"
            and claim["id"] in r["targets"]
            and r["target_versions"].get(claim["id"]) == content_hash(claim, "evidence")
        ]
        if not current:
            return f"obtain independent evidence review for {claim['id']}"
        reviews.extend(r["id"] for r in current)
    decisions = [
        r
        for r, _ in records.values()
        if r["kind"] == "decision"
        and set(r["claims"]).intersection(c["id"] for c in claims)
        and set(r["reviews"]).intersection(reviews)
    ]
    accepted = [r["id"] for r in decisions if r["status"] == "accepted"]
    if accepted:
        return (
            f"complete: decision {', '.join(accepted)} recorded; choose the next research question"
        )
    if decisions:
        return f"resolve proposed decision {decisions[0]['id']} with the principal investigator"
    return (
        f"record a decision citing {', '.join(c['id'] for c in claims)} and their evidence reviews"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.project).resolve()
    records, errors = load_records(root)
    errors += reference_errors(root, records) + policy_errors(root, records)
    experiments = [
        dict(id=r["id"], gate=r["status"], next_action=next_action(r, records))
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
            next(
                (
                    f"{item['id']}: {item['next_action']}"
                    for item in experiments
                    if not item["next_action"].startswith("complete:")
                ),
                f"{experiments[0]['id']}: {experiments[0]['next_action']}",
            )
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
