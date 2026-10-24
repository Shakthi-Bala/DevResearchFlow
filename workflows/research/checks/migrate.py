#!/usr/bin/env python3
"""Upgrade metadata v1→v2 with backups; never rewrite scientific evidence/reviews."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from provenance import STRICT_POLICY, VERSION, identity_errors, policy, receipt_errors
from record_helper import output
from records import load_records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".")
    parser.add_argument("--check", action="store_true", help="show changes without writing")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="enable strict policy only if all existing evidence already satisfies it",
    )
    args = parser.parse_args()
    root = Path(args.project).resolve()
    metadata = output(root, "research/toolkit_version.json")
    original = metadata.read_bytes()
    value = json.loads(original)
    if not isinstance(value, dict) or value.get("format_version", 1) not in (1, 2):
        raise ValueError("only metadata versions 1 and 2 are supported; no evidence was modified")
    existing = policy(root)
    if args.strict:
        records, errors = load_records(root)
        for record, _ in records.values():
            errors += identity_errors(record, records, True)
            errors += receipt_errors(root, record, True)
        if errors:
            raise ValueError(
                "cannot invent historical identities or receipts; keep legacy policy or use a new strict project:\n"
                + "\n".join(errors)
            )
    updated = {**value, "format_version": 2, "toolkit_version": VERSION}
    desired = dict(STRICT_POLICY) if args.strict else existing
    if updated == value and desired == existing:
        print("Already current; no changes")
        return 0
    if args.check:
        print(
            "Would upgrade metadata to v2; scientific records unchanged; strict policy: "
            + str(args.strict)
        )
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = output(root, f".research-toolkit/migrations/{stamp}")
    backup.mkdir(parents=True)
    (backup / "toolkit_version.json").write_bytes(original)
    policy_path = output(root, "research/policy.json")
    if policy_path.exists():
        (backup / "policy.json").write_bytes(policy_path.read_bytes())
    metadata.write_text(json.dumps(updated, indent=2) + "\n")
    policy_path.write_text(json.dumps(desired, indent=2) + "\n")
    print(f"Metadata upgraded; backup: {backup}; scientific evidence unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError) as exc:
        raise SystemExit(f"drf migrate: {exc}")
