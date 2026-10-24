#!/usr/bin/env python3
"""Check schemas, provenance, review prerequisites, and optional Git status transitions."""

import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from check_references import reference_errors
from provenance import identity_errors, policy, receipt_errors, verify_dataset
from records import content_hash, load_records, local_path, parse, schema_errors, sha256

# Explicit workflow transitions; use a new record/version rather than erasing history.
TRANSITIONS = {
    "question": {
        "draft": {"active", "unresolved"},
        "active": {"resolved", "unresolved"},
        "unresolved": {"active"},
    },
    "task": {
        "ready": {"running", "blocked", "cancelled"},
        "running": {"blocked", "reviewed", "cancelled"},
        "blocked": {"ready", "running", "cancelled"},
    },
    "source": {
        "unreviewed": {"source_checked", "disputed", "superseded"},
        "source_checked": {"disputed", "superseded"},
        "disputed": {"source_checked", "superseded"},
    },
    "hypothesis": {
        "proposed": {"under_test", "unresolved", "superseded"},
        "under_test": {"supported_within_scope", "contradicted", "unresolved", "superseded"},
        "supported_within_scope": {"under_test", "unresolved", "superseded"},
        "contradicted": {"under_test", "superseded"},
        "unresolved": {"under_test", "superseded"},
    },
    "experiment": {
        "draft": {"protocol_reviewed", "superseded"},
        "protocol_reviewed": {"draft", "implementation_reviewed", "superseded"},
        "implementation_reviewed": {"draft", "executing", "superseded"},
        "executing": {"completed", "superseded"},
        "completed": {"superseded"},
    },
    "run": {"planned": {"started", "cancelled"}, "started": {"completed", "failed", "cancelled"}},
    "observation": {
        "unreviewed": {"reviewed", "disputed", "superseded"},
        "reviewed": {"disputed", "superseded"},
        "disputed": {"reviewed", "superseded"},
    },
    "claim": {
        "unreviewed": {"source_checked", "provisionally_supported", "disputed", "superseded"},
        "source_checked": {"provisionally_supported", "disputed", "needs_review", "superseded"},
        "provisionally_supported": {"disputed", "needs_review", "superseded"},
        "disputed": {"needs_review", "superseded"},
        "needs_review": {"source_checked", "provisionally_supported", "disputed", "superseded"},
    },
    "review": {"draft": {"completed", "superseded"}, "completed": {"superseded"}},
    "decision": {"proposed": {"accepted", "replaced"}, "accepted": {"replaced"}},
}


def revision_exists(root: Path, revision: str | None) -> bool:
    if not revision:
        return False
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{revision}^{{commit}}"], capture_output=True
    )
    return result.returncode == 0


def policy_errors(root: Path, records: dict[str, tuple[dict[str, Any], Path]]) -> list[str]:
    errors: list[str] = []

    def report(rid, message):
        errors.append(f"{rid}: {message}")

    try:
        settings = policy(root)
    except (ValueError, OSError) as exc:
        return [str(exc)]

    def review_ok(review_id, target, kind, record=None, historical=False):
        review = records.get(review_id, (None, None))[0]
        subject = record or records.get(target, (None, None))[0]
        return bool(
            review
            and subject
            and review["kind"] == "review"
            and review["status"] in ({"completed", "superseded"} if historical else {"completed"})
            and review["review_type"] == kind
            and target in review["targets"]
            and review["disposition"] == "supported_within_scope"
            and review["checks_performed"]
            and not any(
                f["severity"] == "blocking" and not f["resolved"] for f in review["findings"]
            )
            and review["target_versions"].get(target) == content_hash(subject, kind)
        )

    for rid, (r, path) in records.items():
        kind, status = r["kind"], r["status"]
        errors.extend(
            f"{rid}: {message}"
            for message in identity_errors(r, records, settings["review_identity"])
        )
        errors.extend(
            f"{rid}: {message}"
            for message in receipt_errors(root, r, settings["execution_receipts"])
        )
        if kind == "review" and status == "completed":
            if r["disposition"] == "pending" or not r["checks_performed"]:
                report(
                    rid, "completed review requires checks performed and a substantive disposition"
                )
            if r["disposition"] == "supported_within_scope" and any(
                f["severity"] == "blocking" and not f["resolved"] for f in r["findings"]
            ):
                report(rid, "support cannot coexist with unresolved blocking findings")
        if kind == "experiment":
            if status not in {"draft", "superseded"} and not review_ok(
                r["required_reviews"]["protocol"], rid, "protocol"
            ):
                report(rid, "current supporting protocol review required")
            if status in {"implementation_reviewed", "executing", "completed"}:
                if not review_ok(r["required_reviews"]["implementation"], rid, "implementation"):
                    report(rid, "current supporting implementation review required")
                if (
                    not revision_exists(root, r["implementation"]["commit"])
                    or not r["configuration"]["sha256"]
                ):
                    report(
                        rid,
                        "implementation commit must exist locally and configuration hash must be pinned",
                    )
                try:
                    cfg = local_path(root, r["configuration"]["file"])
                    if sha256(cfg) != r["configuration"]["sha256"]:
                        report(rid, "configuration changed; obtain implementation review")
                except ValueError as exc:
                    report(rid, str(exc))
        if kind == "run" and status != "planned":
            if status == "cancelled" and r["started_at"] is None:
                # A planned execution may be cancelled before it starts.
                if not r["finished_at"] or not r["failure_reason"]:
                    report(rid, "pre-start cancellation requires finish time and reason")
                continue
            if not r["started_at"]:
                report(rid, "actual execution requires started_at")
            if not revision_exists(root, r["code_revision"]):
                report(rid, "run code revision is not a local Git commit")
            snapshot = None
            try:
                candidate = parse(local_path(root, r["protocol_snapshot"]["path"]).read_text())
                findings = schema_errors(candidate, "experiment")
                if findings:
                    raise ValueError("; ".join(findings))
                snapshot = candidate
                if (
                    snapshot.get("id") != r["experiment"]
                    or snapshot.get("version") != r["protocol_version"]
                ):
                    report(rid, "protocol snapshot ID/version differs from manifest")
                if content_hash(snapshot, "protocol") != r["protocol_sha256"]:
                    report(rid, "protocol content hash differs from frozen snapshot")
            except (ValueError, KeyError, OSError) as exc:
                snapshot = None
                report(rid, f"invalid protocol snapshot: {exc}")
            if snapshot:
                for stage in ("protocol", "implementation"):
                    if not any(
                        review_ok(review, r["experiment"], stage, snapshot, True)
                        for review in r["reviews"]
                    ):
                        report(
                            rid,
                            f"run must retain a supporting {stage} review of its frozen protocol",
                        )
                if snapshot["implementation"]["commit"] != r["code_revision"]:
                    report(rid, "run code revision differs from implementation reviewed")
                if snapshot["implementation"]["patch"] != r["patch"]:
                    report(rid, "run patch differs from implementation reviewed")
                if snapshot["configuration"]["sha256"] != r["configuration"]["sha256"]:
                    report(rid, "resolved configuration differs from implementation reviewed")
            if status in {"completed", "failed", "cancelled"} and not r["finished_at"]:
                report(rid, "terminal run needs finished_at")
            if status == "completed" and (r["exit_code"] != 0 or r["metrics"] is None):
                report(rid, "completed run requires exit code zero and metrics artifact")
            if status in {"failed", "cancelled"} and not r["failure_reason"]:
                report(rid, "failed/cancelled run requires a reason")
            if status == "failed" and r["exit_code"] == 0 and not r.get("execution"):
                report(rid, "failed run cannot have exit code zero")
            if settings["execution_receipts"] or r.get("dataset", {}).get("manifest_path"):
                try:
                    verify_dataset(root, r["dataset"])
                except (ValueError, OSError, KeyError, TypeError) as exc:
                    report(rid, f"dataset: {exc}")
            if (
                snapshot
                and snapshot["mode"] == "confirmatory"
                and (settings["execution_receipts"] or r.get("registration_commit"))
            ):
                revision = r.get("registration_commit")
                try:
                    if not isinstance(revision, str) or not revision_exists(root, revision):
                        raise ValueError("missing committed protocol registration")
                    ancestor = subprocess.run(
                        ["git", "-C", str(root), "merge-base", "--is-ancestor", revision, "HEAD"],
                        capture_output=True,
                    )
                    if ancestor.returncode:
                        raise ValueError("protocol registration is not an ancestor of HEAD")
                    experiment_path = records[r["experiment"]][1].relative_to(root)
                    registered = subprocess.run(
                        ["git", "-C", str(root), "show", f"{revision}:{experiment_path}"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    target = parse(registered.stdout, experiment_path.suffix == ".md")
                    if target.get("version") != snapshot["version"] or content_hash(
                        target, "protocol"
                    ) != content_hash(snapshot, "protocol"):
                        raise ValueError("registered protocol differs from frozen run protocol")
                    stamp = subprocess.check_output(
                        ["git", "-C", str(root), "show", "-s", "--format=%ct", revision], text=True
                    ).strip()
                    if (
                        not r["started_at"]
                        or int(stamp)
                        > datetime.fromisoformat(
                            r["started_at"].upper().replace("Z", "+00:00")
                        ).timestamp()
                    ):
                        raise ValueError("protocol registration must precede execution")
                except (
                    ValueError,
                    OSError,
                    KeyError,
                    TypeError,
                    subprocess.CalledProcessError,
                ) as exc:
                    report(rid, f"confirmatory preregistration: {exc}")
            if r["started_at"] and r["finished_at"]:
                if datetime.fromisoformat(
                    r["finished_at"].upper().replace("Z", "+00:00")
                ) < datetime.fromisoformat(r["started_at"].upper().replace("Z", "+00:00")):
                    report(rid, "finish time precedes start time")
        if kind in {"claim", "source", "observation", "hypothesis"}:
            review_type = "source" if status == "source_checked" else "evidence"
            promoted = status in {
                "source_checked",
                "provisionally_supported",
                "reviewed",
                "supported_within_scope",
                "contradicted",
            }
            if promoted and not any(
                review_ok(review, rid, review_type) for review in r["review_records"]
            ):
                report(rid, f"{status} requires a current independent {review_type} review")
            if kind == "claim" and status in {"source_checked", "provisionally_supported"}:
                if not r["supporting_evidence"] or not r["check_methods"]:
                    report(rid, "supported claim requires evidence and explicit check methods")
                if status == "source_checked" and not any(
                    records.get(i, ({}, None))[0].get("kind") == "source"
                    for i in r["supporting_evidence"]
                ):
                    report(rid, "source_checked claim requires a source record")
        if (
            kind == "claim"
            and r.get("mode") == "exploratory"
            and status == "provisionally_supported"
        ):
            report(
                rid,
                "exploratory claim cannot be provisionally_supported; define a new confirmatory protocol and claim",
            )
        if (
            kind == "claim"
            and r.get("mode") == "confirmatory"
            and status == "provisionally_supported"
        ):
            seen = set()

            def evidence_runs(reference):
                if reference in seen:
                    return set()
                seen.add(reference)
                item = records.get(reference, ({}, None))[0]
                if item.get("kind") == "run":
                    return {reference}
                if item.get("kind") == "observation":
                    return evidence_runs(item["run"])
                if item.get("kind") == "claim":
                    return set().union(
                        *(evidence_runs(value) for value in item["supporting_evidence"])
                    )
                return set()

            runs = set().union(*(evidence_runs(value) for value in r["supporting_evidence"]))
            if not runs:
                report(rid, "confirmatory claim needs run-backed supporting evidence")
            for run_id in runs:
                run = records[run_id][0]
                experiment = records.get(run["experiment"], ({}, None))[0]
                if experiment.get("mode") != "confirmatory" or not run.get("registration_commit"):
                    report(
                        rid,
                        f"{run_id}: exploratory/unregistered evidence cannot support a confirmatory claim",
                    )
        if (
            kind == "claim"
            and status == "provisionally_supported"
            and settings["execution_receipts"]
            and r.get("mode") != "confirmatory"
        ):
            report(
                rid,
                "strict supported claims must declare mode: confirmatory and cite preregistered run evidence",
            )
        if kind == "task" and status == "reviewed" and not r["outputs"]:
            report(rid, "reviewed task requires output references")
        if kind == "decision" and status == "accepted":
            if r["consequential_change"] and not r["human_direction"]:
                report(rid, "consequential change requires recorded PI direction")
            if r["claims"] and not r["reviews"]:
                report(rid, "decision using claims requires review references")
    # Validate state before looking up references: malformed YAML/types are user errors.
    try:
        state = parse((root / "research/state.yaml").read_text())
        findings = schema_errors(state, "state")
        errors.extend(f"state: {finding}" for finding in findings)
        if not findings:
            for field, kind in [
                ("active_question", "question"),
                ("current_experiment", "experiment"),
            ]:
                value = state[field]
                if value is not None and records.get(value, ({}, None))[0].get("kind") != kind:
                    report("state", f"{field} must reference a {kind}")
            for task in state["active_tasks"]:
                if records.get(task, ({}, None))[0].get("kind") != "task":
                    report("state", f"invalid task {task!r}")
    except (ValueError, OSError) as exc:
        report("state", str(exc))
    return errors


def history_errors(
    root: Path, records: dict[str, tuple[dict[str, Any], Path]], base_ref: str
) -> list[str]:
    errors: list[str] = []
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode:
        return [f"--base-ref {base_ref}: project is not in a Git repository"]
    top = Path(result.stdout.strip()).resolve()
    valid = subprocess.run(
        [
            "git",
            "-C",
            str(top),
            "rev-parse",
            "--verify",
            "--end-of-options",
            f"{base_ref}^{{commit}}",
        ],
        capture_output=True,
        text=True,
    )
    if valid.returncode:
        return [f"invalid --base-ref: {base_ref}"]
    base_ref = valid.stdout.strip()
    for rid, (record, path) in records.items():
        old = subprocess.run(
            ["git", "-C", str(top), "show", f"{base_ref}:{path.relative_to(top)}"],
            capture_output=True,
            text=True,
        )
        if old.returncode:
            continue
        try:
            previous = parse(old.stdout, path.suffix == ".md")
        except ValueError as exc:
            errors.append(f"{rid}: cannot parse baseline: {exc}")
            continue
        findings = schema_errors(previous, record["kind"])
        if findings:
            errors.append(f"{rid}: invalid baseline record: {findings[0]}")
            continue
        before, after = previous.get("status"), record["status"]
        executed_transition = (
            record["kind"] == "run"
            and before == "planned"
            and after in {"completed", "failed", "cancelled"}
            and bool(record.get("execution"))
            and not receipt_errors(root, record, True)
        )
        if (
            before != after
            and after not in TRANSITIONS[record["kind"]].get(before, set())
            and not executed_transition
        ):
            errors.append(
                f"{rid}: forbidden transition {before} -> {after}; record intermediate gates in Git"
            )
        if record["version"] < previous.get("version", 1):
            errors.append(f"{rid}: version moved backwards")
        if (
            record["kind"] == "run"
            and before in {"completed", "failed", "cancelled"}
            and previous != record
        ):
            errors.append(
                f"{rid}: terminal run evidence is immutable; create a new run or correction record"
            )
        if record["kind"] == "experiment" and previous.get("status") != "draft":
            if (
                content_hash(previous, "protocol") != content_hash(record, "protocol")
                and record["version"] <= previous["version"]
            ):
                errors.append(f"{rid}: changed protocol requires a new version and review")
    relative = root.relative_to(top)
    run_prefix = str(relative / "runs")
    listing = subprocess.run(
        ["git", "-C", str(top), "ls-tree", "-r", "--name-only", base_ref, "--", run_prefix],
        capture_output=True,
        text=True,
    )
    for name in listing.stdout.splitlines():
        if not name.endswith("/manifest.yaml") or (top / name).exists():
            continue
        old = subprocess.run(
            ["git", "-C", str(top), "show", f"{base_ref}:{name}"], capture_output=True, text=True
        )
        try:
            previous = parse(old.stdout)
        except ValueError:
            continue
        if previous.get("kind") == "run":
            errors.append(
                f"{previous.get('id')}: recorded run manifest was deleted; preserve execution evidence"
            )
    return errors


def main() -> bool:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument(
        "--base-ref",
        help="compare allowed transitions and immutable runs against a Git commit (e.g. HEAD)",
    )
    args = parser.parse_args()
    root = Path(args.project).resolve()
    records, errors = load_records(root)
    errors.extend(reference_errors(root, records))
    errors.extend(policy_errors(root, records))
    if args.base_ref:
        errors.extend(history_errors(root, records, args.base_ref))
    for error in errors:
        print(error)
    print(
        f"{len(records)} records; {len(errors)} errors. Structural validity does not establish scientific support."
    )
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
