#!/usr/bin/env python3
"""Create draft records and capture provenance without granting review approval."""

import argparse
import copy
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from records import FOLDERS, content_hash, local_path, parse, schema_errors, sha256, yaml

PREFIXES = dict(
    zip(
        [
            "question",
            "task",
            "source",
            "hypothesis",
            "experiment",
            "observation",
            "claim",
            "review",
            "decision",
            "run",
        ],
        ["Q", "TASK", "SRC", "HYP", "EXP", "OBS", "CLM", "REV", "DEC", "RUN"],
    )
)


def read(path: Path) -> dict[str, Any]:
    return parse(path.read_text(), path.suffix == ".md")


def output(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("output must be relative to the project")
    dest = root / path
    for part in [dest, *dest.parents]:
        if part == root:
            break
        if part.is_symlink():
            raise ValueError(f"refusing symlinked output: {relative}")
    return dest


def save(path: Path, record: dict[str, Any], markdown: bool = False) -> None:
    errors = schema_errors(record, record["kind"])
    if errors:
        raise ValueError("; ".join(errors))
    if record["kind"] != "run" and any(
        path.with_suffix(ext).exists() for ext in (".md", ".yaml", ".yml", ".json")
    ):
        raise ValueError("record ID already exists; use a fresh ID")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: never rewrite a reviewed record or terminal manifest.
    with path.open("x") as stream:
        data = yaml.safe_dump(record, sort_keys=False)
        stream.write("---\n" + data + "---\n" if markdown else data)
    print(path)


def template(kind: str) -> dict[str, Any]:
    path = next((Path(__file__).resolve().parent.parent / "templates").glob(kind + ".*"))
    return read(path)


def rewrite(path: Path, record: dict[str, Any]) -> None:
    """Preserve Markdown narrative and JSON serialization on a checked update."""
    body = ""
    if path.suffix == ".md":
        lines = path.read_text().splitlines(keepends=True)
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
        body = "".join(lines[end + 1 :])
    payload = yaml.safe_dump(record, sort_keys=False)
    if path.suffix == ".md":
        payload = "---\n" + payload + "---\n" + body
    elif path.suffix == ".json":
        payload = json.dumps(record, indent=2) + "\n"
    path.write_text(payload)


def advance(root: Path, rid: str, status: str, reviews: list[str]) -> None:
    from check_references import reference_errors
    from records import load_records
    from validate_records import TRANSITIONS, history_errors, policy_errors, revision_exists

    records, errors = load_records(root)
    errors += reference_errors(root, records) + policy_errors(root, records)
    if errors:
        raise ValueError("repair project validation first: " + "; ".join(errors))
    if rid not in records or records[rid][0]["kind"] != "experiment":
        raise ValueError("advance requires an existing experiment ID")
    record, path = records[rid]
    if status not in TRANSITIONS["experiment"].get(record["status"], set()):
        raise ValueError(f"forbidden transition {record['status']} -> {status}")
    candidate = copy.deepcopy(record)
    candidate["status"] = status
    stage = {"protocol_reviewed": "protocol", "implementation_reviewed": "implementation"}.get(
        status
    )
    if reviews and not stage:
        raise ValueError("--review applies only to protocol_reviewed or implementation_reviewed")
    if len(reviews) > 1:
        raise ValueError("provide one review for the gate")
    for review_id in reviews:
        review = records.get(review_id, ({}, None))[0]
        if (
            review.get("kind") != "review"
            or review.get("review_type") != stage
            or rid not in review.get("targets", [])
        ):
            raise ValueError("review must target this experiment and match the gate")
        candidate["required_reviews"][stage] = review_id
    linked_runs = [
        v[0] for v in records.values() if v[0]["kind"] == "run" and v[0]["experiment"] == rid
    ]
    if status == "executing" and not any(run["started_at"] for run in linked_runs):
        raise ValueError("execute a planned run before advancing to executing")
    if status == "completed" and (
        not linked_runs or any(run["status"] in {"planned", "started"} for run in linked_runs)
    ):
        raise ValueError("complete or cancel every linked run before completing the experiment")
    records[rid] = (candidate, path)
    errors = (
        schema_errors(candidate, "experiment")
        + reference_errors(root, records)
        + policy_errors(root, records)
    )
    if revision_exists(root, "HEAD"):
        errors += history_errors(root, records, "HEAD")
    if errors:
        raise ValueError("gate rejected: " + "; ".join(errors))
    output(root, str(path.relative_to(root)))
    rewrite(path, candidate)
    print(f"{rid}: {record['status']} -> {status}; commit this gate before advancing again")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".")
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser(
        "new", help="create a draft from a template; fill SET_ME fields yourself"
    )
    new.add_argument("kind", choices=PREFIXES)
    new.add_argument("id")
    new.add_argument("--model", default="SET_ME")
    new.add_argument("--session", default="SET_ME")
    new.add_argument("--mode", choices=["exploratory", "confirmatory"])
    review = commands.add_parser(
        "review", help="create a pending review with current target hashes"
    )
    review.add_argument("id")
    review.add_argument("--model", default="SET_ME")
    review.add_argument("--session", default="SET_ME")
    review.add_argument(
        "--supersedes", help="supersede an existing review, preserving its findings and narrative"
    )
    review.add_argument(
        "--type", required=True, choices=["protocol", "implementation", "source", "evidence"]
    )
    review.add_argument("targets", nargs="+", help="project-relative record paths")
    pin = commands.add_parser(
        "pin", help="print implementation/configuration fields for a draft experiment"
    )
    pin.add_argument("experiment")
    pin.add_argument("--write", action="store_true", help="write pinned fields into the draft")
    step = commands.add_parser("advance", help="validate and write the next experiment gate")
    step.add_argument("id")
    step.add_argument("status")
    step.add_argument("--review", action="append", default=[])
    run = commands.add_parser(
        "prepare-run", help="capture a planned run and frozen provenance; does not execute"
    )
    run.add_argument("id")
    run.add_argument("experiment")
    run.add_argument(
        "--environment", required=True, help="existing project-relative environment capture"
    )
    run.add_argument("--seed", type=int)
    run.add_argument("--dataset-version", required=True)
    run.add_argument("--dataset-manifest", required=True)
    run.add_argument("--device", required=True)
    run.add_argument("--exec", dest="argv", nargs=argparse.REMAINDER, required=True)
    artifact = commands.add_parser(
        "artifact", help="print a path/checksum mapping without changing records"
    )
    artifact.add_argument("path")
    dataset = commands.add_parser(
        "dataset-manifest", help="hash all files under explicit project-relative data inputs"
    )
    dataset.add_argument("output")
    dataset.add_argument("inputs", nargs="+")
    args = parser.parse_args()
    root = Path(args.project).expanduser().resolve()
    if args.command == "advance":
        advance(root, args.id, args.status, args.review)
        return
    if args.command == "dataset-manifest":
        from provenance import data_files

        dest = output(root, args.output)
        for value in args.inputs:
            base = (root / value).resolve()
            if dest.resolve() == base or (base.is_dir() and dest.resolve().is_relative_to(base)):
                raise ValueError("write the manifest outside its input files/directories")
        files = data_files(root, args.inputs)
        if not files:
            raise ValueError("dataset inputs contain no files")
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("x") as stream:
            json.dump(
                {"format_version": 1, "inputs": args.inputs, "files": files}, stream, indent=2
            )
            stream.write("\n")
        print(dest)
        return
    if args.command == "artifact":
        path = local_path(root, args.path)
        print(yaml.safe_dump({"path": args.path, "sha256": sha256(path)}, sort_keys=False), end="")
        return
    if args.command == "pin":
        record = read(local_path(root, args.experiment))
        if record.get("kind") != "experiment" or record.get("status") != "draft":
            raise ValueError("pin a draft experiment, then obtain fresh reviews")
        local_path(root, record["implementation"]["file"])
        commit = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
        changes = subprocess.check_output(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--porcelain",
                "--",
                record["implementation"]["file"],
                record["configuration"]["file"],
            ],
            text=True,
        )
        if changes:
            raise ValueError("commit implementation and configuration before pinning")
        implementation = {**record["implementation"], "commit": commit}
        if args.write:
            record["implementation"] = implementation
            record["configuration"]["sha256"] = sha256(
                local_path(root, record["configuration"]["file"])
            )
            errors = schema_errors(record, "experiment")
            if errors:
                raise ValueError("; ".join(errors))
            path = output(root, args.experiment)
            rewrite(path, record)
            print(path)
            return
        print(
            yaml.safe_dump(
                {
                    "implementation": implementation,
                    "configuration": {
                        **record["configuration"],
                        "sha256": sha256(local_path(root, record["configuration"]["file"])),
                    },
                },
                sort_keys=False,
            ),
            end="",
        )
        return
    if args.command == "new":
        record = template(args.kind)
        record["id"] = args.id
        if args.kind in {"claim", "experiment"}:
            record["mode"] = args.mode or "exploratory"
        elif args.mode:
            raise ValueError("--mode applies only to experiments and claims")
        role = {
            "question": "coordinator",
            "task": "coordinator",
            "source": "literature",
            "hypothesis": "hypothesis",
            "experiment": "methodology",
            "observation": "analyst",
            "claim": "analyst",
            "review": "verifier",
            "decision": "coordinator",
            "run": "engineer",
        }[args.kind]
        record["author"] = {"role": role, "model": args.model, "session": args.session}
        if args.kind == "experiment":
            record["implementation"]["author"] = {
                "role": "engineer",
                "model": "SET_ME",
                "session": "SET_ME",
            }
        folder = {v: k for k, v in FOLDERS.items()}.get(args.kind)
        relative = (
            f"research/{folder}/{args.id}.yaml" if folder else f"runs/{args.id}/manifest.yaml"
        )
        save(output(root, relative), record)
        return
    if args.command == "review":
        record = template("review")
        record.update(
            id=args.id,
            review_type=args.type,
            targets=[],
            target_versions={},
            reviewer={"role": "verifier", "model": args.model, "session": args.session},
        )
        allowed = {
            "protocol": {"experiment"},
            "implementation": {"experiment"},
            "source": {"source", "claim"},
            "evidence": {"claim", "observation", "hypothesis"},
        }
        for name in args.targets:
            target = read(local_path(root, name))
            if target.get("kind") not in allowed[args.type]:
                raise ValueError("wrong target kind for this review type")
            if schema_errors(target, target["kind"]):
                raise ValueError(f"invalid target: {name}")
            record["targets"].append(target["id"])
            record["target_versions"][target["id"]] = content_hash(target, args.type)
        previous = None
        if args.supersedes:
            from records import load_records

            records, _ = load_records(root)
            previous = records.get(args.supersedes)
            if (
                not previous
                or previous[0]["kind"] != "review"
                or previous[0]["review_type"] != args.type
            ):
                raise ValueError("--supersedes must name an existing review of the same type")
            if set(previous[0]["targets"]) != set(record["targets"]):
                raise ValueError("replacement review must retain the same target IDs")
            if previous[0]["status"] == "superseded":
                raise ValueError("review already superseded; name the latest review instead")
            record["supersedes"] = args.supersedes
        save(output(root, f"research/reviews/{args.id}.yaml"), record)
        if previous:
            prior, path = previous
            output(root, str(path.relative_to(root)))
            prior["status"] = "superseded"
            text = path.read_text()
            body = ""
            if path.suffix == ".md":
                lines = text.splitlines(keepends=True)
                end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
                body = "".join(lines[end + 1 :])
            payload = yaml.safe_dump(prior, sort_keys=False)
            if path.suffix == ".md":
                payload = "---\n" + payload + "---\n" + body
            if path.suffix == ".json":
                payload = json.dumps(prior, indent=2) + "\n"
            path.write_text(payload)

        return
    # Check existing records before reserving a new run directory.
    from check_references import reference_errors
    from records import load_records
    from validate_records import policy_errors

    records, errors = load_records(root)
    errors += reference_errors(root, records) + policy_errors(root, records)
    if errors:
        raise ValueError("repair project validation first: " + "; ".join(errors))
    experiment = read(local_path(root, args.experiment))
    if (
        experiment.get("kind") != "experiment"
        or experiment.get("status") != "implementation_reviewed"
    ):
        raise ValueError("prepare-run requires an implementation_reviewed experiment")
    if not re.fullmatch(r"RUN-[0-9]{3,}", args.id) or not args.argv:
        raise ValueError("provide RUN-NNN and a nonempty --exec command")
    config = local_path(root, experiment["configuration"]["file"]).read_bytes()
    environment = local_path(root, args.environment).read_bytes()
    dataset_path = local_path(root, args.dataset_manifest)
    dataset_hash = sha256(dataset_path)
    record = template("run")
    prefix = f"runs/{args.id}"
    record.update(
        id=args.id,
        scope=experiment["scope"],
        experiment=experiment["id"],
        protocol_version=experiment["version"],
        protocol_sha256=content_hash(experiment, "protocol"),
        code_revision=experiment["implementation"]["commit"],
        patch=experiment["implementation"]["patch"],
        command=args.argv,
        seed=args.seed,
        hardware={"device": args.device},
        dataset={"version": args.dataset_version, "manifest_sha256": dataset_hash},
        reviews=list(experiment["required_reviews"].values()),
    )
    try:
        dataset_manifest = json.loads(dataset_path.read_text())
        if dataset_manifest.get("format_version") == 1 and "files" in dataset_manifest:
            record["dataset"]["manifest_path"] = args.dataset_manifest
    except (ValueError, AttributeError):
        pass
    dest = output(root, prefix)
    if dest.exists():
        raise ValueError("run directory already exists; choose a fresh run ID")
    dest.mkdir(parents=True)
    (dest / "protocol.yaml").write_text(yaml.safe_dump(experiment, sort_keys=False))
    (dest / "config_resolved.yaml").write_bytes(config)
    (dest / "environment.txt").write_bytes(environment)
    for field, name in [
        ("protocol_snapshot", "protocol.yaml"),
        ("configuration", "config_resolved.yaml"),
        ("environment", "environment.txt"),
    ]:
        record[field] = {"path": f"{prefix}/{name}", "sha256": sha256(dest / name)}
    record["logs"] = {name: f"{prefix}/{name}.log" for name in ("stdout", "stderr")}
    save(dest / "manifest.yaml", record)
    print(
        "Planned only. Execute with drf run to capture timestamps, logs, environment, exit code and artifacts."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, StopIteration, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"record-helper: {exc}")
