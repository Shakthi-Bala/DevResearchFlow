"""Policy, identity, dataset, and receipt verification shared by runner and checks."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from records import content_hash, local_path, parse, sha256

VERSION = (Path(__file__).resolve().parents[1] / "VERSION").read_text().strip()
STRICT_POLICY = {
    "format_version": 2,
    "execution_receipts": True,
    "review_identity": True,
}
LEGACY_POLICY = {
    "format_version": 1,
    "execution_receipts": False,
    "review_identity": False,
}


def policy(root: Path) -> dict[str, Any]:
    path = root / "research/policy.json"
    if not path.exists():
        metadata = root / "research/toolkit_version.json"
        if metadata.exists() and json.loads(metadata.read_text()).get("format_version", 1) >= 2:
            raise ValueError(
                "missing research/policy.json in a versioned project; restore its committed policy"
            )
        return dict(LEGACY_POLICY)
    value = json.loads(local_path(root, "research/policy.json").read_text())
    if not isinstance(value, dict) or value.get("format_version") not in (1, 2):
        raise ValueError("unsupported research/policy.json; use drf migrate --help")
    for field in ("execution_receipts", "review_identity"):
        if not isinstance(value.get(field), bool):
            raise ValueError(f"research/policy.json requires boolean {field}")
    return value


def manifest_hash(record: dict[str, Any]) -> str:
    data = {k: v for k, v in record.items() if k != "execution"}
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def identity_errors(record: dict[str, Any], records: dict[str, Any], strict: bool) -> list[str]:
    if record["kind"] != "review" or record["status"] != "completed":
        return []
    errors = []
    reviewer = record["reviewer"]
    if strict and (not isinstance(reviewer, dict) or not complete_identity(reviewer)):
        errors.append("reviewer identity is required: record actual role, model and fresh session")
    for target in record["targets"]:
        subject = records.get(target, ({}, None))[0]
        author = subject.get("author")
        if strict and (not isinstance(author, dict) or not complete_identity(author)):
            errors.append(f"{target}: author identity is required before review")
        implementation_author = (
            subject.get("implementation", {}).get("author")
            if record["review_type"] == "implementation"
            else None
        )
        if (
            strict
            and record["review_type"] == "implementation"
            and not (
                isinstance(implementation_author, dict) and complete_identity(implementation_author)
            )
        ):
            errors.append(
                f"{target}: implementation.author identity is required before code review"
            )
        if (
            isinstance(implementation_author, dict)
            and isinstance(reviewer, dict)
            and complete_identity(implementation_author)
            and complete_identity(reviewer)
            and implementation_author["session"] == reviewer["session"]
        ):
            errors.append(f"{target}: self-review session for implementation author")
        if isinstance(author, dict) and isinstance(reviewer, dict):
            if (
                complete_identity(author)
                and complete_identity(reviewer)
                and author["session"] == reviewer["session"]
            ):
                errors.append(
                    f"{target}: self-review session; start a fresh reviewer session, preferably with a different model"
                )
    return errors


def complete_identity(value: dict[str, Any]) -> bool:
    return all(
        isinstance(value.get(k), str) and value[k].strip() and "SET_ME" not in value[k]
        for k in ("role", "model", "session")
    )


def data_files(root: Path, inputs: list[str]) -> list[dict[str, Any]]:
    files = {}
    for value in inputs:
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts or ".git" in relative.parts:
            raise ValueError("dataset inputs must be project-relative, outside .git")
        base = root / relative
        # Resolve every component; never follow dataset symlinks.
        for component in [base, *base.parents]:
            if component == root:
                break
            if component.is_symlink():
                raise ValueError(f"dataset symlink is not supported: {value}")
        if not base.exists():
            raise ValueError(f"missing dataset input: {value}")
        candidates = sorted(base.rglob("*")) if base.is_dir() else [base]
        for path in candidates:
            if path.is_symlink():
                raise ValueError(f"dataset symlink is not supported: {path.relative_to(root)}")
            if path.is_file():
                name = path.relative_to(root).as_posix()
                files[name] = {"path": name, "sha256": sha256(path), "size": path.stat().st_size}
    return [files[name] for name in sorted(files)]


def verify_dataset(root: Path, dataset: dict[str, Any]) -> None:
    path = local_path(root, dataset["manifest_path"])
    if sha256(path) != dataset["manifest_sha256"]:
        raise ValueError("dataset manifest checksum mismatch; regenerate and review the dataset")
    manifest = json.loads(path.read_text())
    if not isinstance(manifest, dict) or manifest.get("format_version") != 1:
        raise ValueError("use drf dataset-manifest to create a per-file dataset manifest")
    inputs = manifest.get("inputs")
    if not isinstance(inputs, list) or not inputs or not all(isinstance(v, str) for v in inputs):
        raise ValueError("dataset manifest needs nonempty inputs")
    if data_files(root, inputs) != manifest.get("files"):
        raise ValueError(
            "dataset files changed, added or removed; create a new manifest and obtain review"
        )


def registration(root: Path, record: dict[str, Any], experiment_path: Path) -> str | None:
    relative = str(experiment_path.relative_to(root))
    result = subprocess.run(
        ["git", "-C", str(root), "log", "--format=%H", "--", relative],
        capture_output=True,
        text=True,
        check=True,
    )
    for revision in result.stdout.splitlines():
        blob = subprocess.run(
            ["git", "-C", str(root), "show", f"{revision}:{relative}"],
            capture_output=True,
            text=True,
        )
        if blob.returncode:
            continue
        try:
            candidate = parse(blob.stdout, experiment_path.suffix == ".md")
            if candidate.get("version") == record["version"] and content_hash(
                candidate, "protocol"
            ) == content_hash(record, "protocol"):
                return revision
        except (ValueError, KeyError, TypeError):
            continue
    return None


def receipt_errors(root: Path, record: dict[str, Any], required: bool) -> list[str]:
    if (
        record["kind"] != "run"
        or record["status"] == "planned"
        or (record["status"] == "cancelled" and not record["started_at"])
    ):
        return []
    receipt = record.get("execution")
    if not receipt:
        return (
            ["execution receipt required; execute a fresh planned run with drf run RUN-NNN"]
            if required
            else []
        )
    try:
        path = local_path(root, receipt["path"])
        if sha256(path) != receipt["sha256"]:
            raise ValueError("execution receipt checksum mismatch")
        value = json.loads(path.read_text())
        if value.get("format_version") != 1 or value.get("producer") != "devresearchflow.execute":
            raise ValueError("unsupported execution receipt")
        if value.get("manifest_sha256") != manifest_hash(record):
            raise ValueError(
                "run manifest differs from execution receipt; retain evidence and create a correction record"
            )
        files = value.get("files")
        if not isinstance(files, dict):
            raise ValueError("execution receipt needs file checksums")
        expected = set(record["logs"].values())
        for field in ("configuration", "environment", "protocol_snapshot", "metrics", "patch"):
            if record.get(field):
                expected.add(record[field]["path"])
        expected.update(item["path"] for item in record["artifacts"])
        if record["dataset"].get("manifest_path"):
            expected.add(record["dataset"]["manifest_path"])
        if set(files) != expected:
            raise ValueError("execution receipt must cover all run evidence, including logs")
        for name, digest in files.items():
            if record["status"] == "started" and name in record["logs"].values():
                continue  # Live logs are sealed only when execution ends.
            if sha256(local_path(root, name)) != digest:
                raise ValueError(f"execution evidence changed: {name}")
        return []
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        return [str(exc)]
