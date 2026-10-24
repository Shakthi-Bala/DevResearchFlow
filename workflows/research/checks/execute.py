#!/usr/bin/env python3
"""Execute a reviewed planned run and capture evidence. Receipts are not signatures."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import distributions
from pathlib import Path
from typing import Any

from check_references import reference_errors
from provenance import VERSION, manifest_hash, registration, verify_dataset
from record_helper import output
from records import load_records, local_path, parse, sha256, yaml
from validate_records import policy_errors


def capture_environment(root: Path, record: dict[str, Any]) -> dict[str, str]:
    """Capture the runner and explicitly identified Python command environment."""

    def probe(command: list[str]) -> dict[str, Any]:
        try:
            result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=15)
            return {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"command": command, "unavailable": str(exc)}

    executable = record["command"][0]
    resolved = shutil.which(executable)
    captured: dict[str, Any] = {
        "format_version": 1,
        "captured_at": now(),
        "runner": {
            "executable": sys.executable,
            "version": sys.version,
            "packages": sorted(
                ({"name": d.metadata["Name"] or "", "version": d.version} for d in distributions()),
                key=lambda d: (d["name"], d["version"]),
            ),
        },
        "platform": platform.platform(),
        "command_executable": {"requested": executable, "resolved": resolved},
        "variables": {
            key: os.environ.get(key)
            for key in (
                "CUDA_VISIBLE_DEVICES",
                "NVIDIA_VISIBLE_DEVICES",
                "PYTHONHASHSEED",
                "OMP_NUM_THREADS",
                "MKL_NUM_THREADS",
                "CUBLAS_WORKSPACE_CONFIG",
            )
        },
        "gpu": probe(
            [
                "nvidia-smi",
                "--query-gpu=name,uuid,driver_version,memory.total",
                "--format=csv,noheader",
            ]
        ),
    }
    if re.fullmatch(r"python(?:[0-9]+(?:\.[0-9]+)*)?", Path(executable).name):
        captured["command_python"] = probe(
            [
                executable,
                "-c",
                "import sys,json,importlib.metadata as m; print(json.dumps({'executable':sys.executable,'version':sys.version,'packages':sorted([(d.metadata['Name'] or '',d.version) for d in m.distributions()])}))",
            ]
        )
    else:
        captured["command_python"] = {
            "unavailable": "command is not a direct Python interpreter; runner packages may differ"
        }
    relative = f"runs/{record['id']}/environment-captured.json"
    path = output(root, relative)
    with path.open("x") as stream:
        json.dump(captured, stream, indent=2)
        stream.write("\n")
    return {"path": relative, "sha256": sha256(path)}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def is_record(name: str) -> bool:
    return name.startswith(("research/", "runs/", ".research-toolkit/"))


def checked_code_tree(root: Path, revision: str) -> str:
    """Check every tracked non-record file and reject untracked non-record inputs."""
    expected: dict[str, tuple[str, str]] = {}
    for entry in git(root, "ls-tree", "-rz", revision).split(b"\0"):
        if not entry:
            continue
        meta, name_bytes = entry.split(b"\t", 1)
        mode, _, oid = meta.decode().split()
        name = os.fsdecode(name_bytes)
        if not is_record(name):
            expected[name] = (mode, oid)
    current = {os.fsdecode(p) for p in git(root, "ls-files", "-z").split(b"\0") if p}
    current = {p for p in current if not is_record(p)}
    if current != set(expected):
        raise ValueError(
            "tracked code/input files differ from reviewed commit; commit changes and obtain implementation review"
        )
    untracked = [
        os.fsdecode(p)
        for p in git(root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
        if p
    ]
    if any(not is_record(p) for p in untracked):
        raise ValueError(
            "untracked non-record files exist; commit reviewed inputs or move unrelated files outside the project"
        )
    hashes = {}
    for name, (mode, oid) in expected.items():
        if mode not in ("100644", "100755"):
            raise ValueError(f"unsupported execution input symlink/submodule: {name}")
        path = local_path(root, name)
        # local_path contains symlink escapes, but execution also disallows aliases.
        if path != root / name or (root / name).is_symlink():
            raise ValueError(f"symlinked execution input: {name}")
        data = path.read_bytes()
        if data != git(root, "cat-file", "blob", oid):
            raise ValueError(
                f"code/input differs from reviewed commit: {name}; commit it and obtain fresh review"
            )
        if os.name == "posix" and bool(path.stat().st_mode & 0o111) != (mode == "100755"):
            raise ValueError(f"executable mode differs from reviewed commit: {name}")
        hashes[name] = hashlib.sha256(data).hexdigest()
    # Also reject staged changes that happen to be repaired only in the worktree.
    staged = [
        os.fsdecode(p)
        for p in git(root, "diff", "--cached", "--name-only", "-z", revision).split(b"\0")
        if p
    ]
    if any(not is_record(p) for p in staged):
        raise ValueError("staged code/input changes differ from reviewed commit")
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def write_manifest(path: Path, record: dict[str, Any]) -> None:
    temporary = output(path.parent, ".manifest-writing.yaml")
    with temporary.open("x") as stream:
        stream.write(yaml.safe_dump(record, sort_keys=False))
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def seal(root: Path, record: dict[str, Any], tree: str, phase: str) -> None:
    names = set(record["logs"].values())
    for field in ("configuration", "environment", "protocol_snapshot", "metrics", "patch"):
        if record.get(field):
            names.add(record[field]["path"])
    names.update(item["path"] for item in record["artifacts"])
    if record["dataset"].get("manifest_path"):
        names.add(record["dataset"]["manifest_path"])
    receipt = {
        "format_version": 1,
        "producer": "devresearchflow.execute",
        "toolkit_version": VERSION,
        "phase": phase,
        "manifest_sha256": manifest_hash(record),
        "code_tree_sha256": tree,
        "files": {name: sha256(local_path(root, name)) for name in sorted(names)},
    }
    relative = f"runs/{record['id']}/execution-{phase}.json"
    path = output(root, relative)
    with path.open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    record["execution"] = {"path": relative, "sha256": sha256(path)}


def terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGTERM)
    else:
        process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait()


def execute(root: Path, rid: str, metrics: str, artifacts: list[str], timeout: float | None) -> int:
    if not re.fullmatch(r"RUN-[0-9]{3,}", rid):
        raise ValueError("use a run ID such as RUN-001")
    top = Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel")).strip()).resolve()
    if top != root:
        raise ValueError("run from the Git project root")
    records, errors = load_records(root)
    errors += reference_errors(root, records) + policy_errors(root, records)
    if errors:
        raise ValueError("repair project validation before execution:\n" + "\n".join(errors))
    record, path = records.get(rid, (None, None))
    if record is None or record["kind"] != "run" or record["status"] != "planned":
        raise ValueError(
            "execute requires a fresh planned run; terminal/started runs cannot be rerun"
        )
    snapshot = parse(local_path(root, record["protocol_snapshot"]["path"]).read_text())
    experiment, experiment_path = records[record["experiment"]]
    if experiment["status"] not in ("implementation_reviewed", "executing"):
        raise ValueError("experiment must be implementation_reviewed or executing")
    if snapshot["implementation"]["patch"] or record["patch"]:
        raise ValueError(
            "runner requires committed code without a patch; commit it and obtain fresh implementation review"
        )
    # Planned runs normally skip evidence checks; execute must check them now.
    for field in ("protocol_snapshot", "configuration", "environment"):
        if sha256(local_path(root, record[field]["path"])) != record[field]["sha256"]:
            raise ValueError(f"planned {field} checksum mismatch")
    from records import content_hash

    if content_hash(snapshot, "protocol") != record["protocol_sha256"] or content_hash(
        snapshot, "implementation"
    ) != content_hash(experiment, "implementation"):
        raise ValueError(
            "planned protocol differs from current reviewed experiment; prepare a fresh run"
        )
    if (
        sha256(local_path(root, experiment["configuration"]["file"]))
        != record["configuration"]["sha256"]
    ):
        raise ValueError("resolved configuration differs from reviewed configuration")
    verify_dataset(root, record["dataset"])
    tree = checked_code_tree(root, record["code_revision"])
    registered = registration(root, snapshot, experiment_path)
    if snapshot["mode"] == "confirmatory" and not registered:
        raise ValueError(
            "confirmatory protocol must be committed before execution; commit the reviewed protocol first"
        )
    record["registration_commit"] = registered
    run_dir = path.parent
    outputs = []
    for name in [metrics, *artifacts]:
        if name in {
            "manifest.yaml",
            "stdout.log",
            "stderr.log",
            "protocol.yaml",
            "config_resolved.yaml",
            "environment.txt",
            "environment-captured.json",
        } or Path(name).name.startswith((".execution", "execution-", ".manifest-")):
            raise ValueError("declared output conflicts with reserved execution evidence")
        dest = output(run_dir, name)
        if dest == run_dir or not dest.is_relative_to(run_dir):
            raise ValueError("outputs must be run-relative files")
        if dest.exists():
            raise ValueError(f"output already exists: {name}; use a fresh run ID")
        if dest in outputs:
            raise ValueError("declared output paths must be unique")
        outputs.append(dest)
    # Logs are fixed to the run directory and opened exclusively.
    record["logs"] = {key: f"runs/{rid}/{key}.log" for key in ("stdout", "stderr")}
    log_paths = [output(root, value) for value in record["logs"].values()]
    if any(p.exists() for p in log_paths):
        raise ValueError("logs already exist; preserve them and choose a fresh run ID")
    lock = output(root, f"runs/{rid}/.execution-lock")
    with lock.open("x") as stream:
        json.dump({"pid": os.getpid(), "started_at": now()}, stream)
    record["command"] = [arg.replace("{run_dir}", f"runs/{rid}") for arg in record["command"]]
    captured_environment = capture_environment(root, record)
    record["artifacts"] = [captured_environment]
    record.update(status="started", started_at=now(), origin="measured")
    process: subprocess.Popen[bytes] | None = None
    interrupted = False
    reason = None
    previous = signal.getsignal(signal.SIGTERM)

    def stop(_signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    try:
        with log_paths[0].open("xb") as stdout, log_paths[1].open("xb") as stderr:
            seal(root, record, tree, "started")
            write_manifest(path, record)
            try:
                env = dict(os.environ, DRF_RUN_DIR=str(run_dir))
                process = subprocess.Popen(
                    record["command"],
                    cwd=root,
                    env=env,
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=(os.name == "posix"),
                )
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                assert process is not None
                terminate(process)
                code = process.returncode
                reason = f"execution exceeded timeout of {timeout} seconds"
            except KeyboardInterrupt:
                interrupted = True
                if process:
                    terminate(process)
                code = process.returncode if process else -signal.SIGINT
                reason = "execution interrupted; partial evidence retained"
            except OSError as exc:
                code = 127
                reason = f"could not launch command: {exc}"
                stderr.write((reason + "\n").encode())
    finally:
        signal.signal(signal.SIGTERM, previous)
    record.update(
        finished_at=now(),
        exit_code=code,
        status="cancelled"
        if interrupted
        else ("completed" if code == 0 and not reason else "failed"),
    )
    record["artifacts"] = [captured_environment]
    for index, dest in enumerate(outputs):
        if dest.is_file() and not dest.is_symlink():
            artifact = {"path": dest.relative_to(root).as_posix(), "sha256": sha256(dest)}
            if index == 0:
                record["metrics"] = artifact
            else:
                record["artifacts"].append(artifact)
        elif record["status"] == "completed":
            reason = f"command exited zero but declared output is missing or unsafe: {dest.name}"
            record["status"] = "failed"
    try:
        if checked_code_tree(root, record["code_revision"]) != tree:
            raise ValueError("reviewed inputs changed during execution")
        verify_dataset(root, record["dataset"])
        if sha256(local_path(root, captured_environment["path"])) != captured_environment["sha256"]:
            raise ValueError("captured environment changed during execution")
        for field in ("protocol_snapshot", "configuration", "environment"):
            if sha256(local_path(root, record[field]["path"])) != record[field]["sha256"]:
                raise ValueError(f"captured {field} changed during execution")
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        reason = f"execution inputs changed: {exc}"
        record["status"] = "failed"
    if record["status"] in ("failed", "cancelled"):
        record["failure_reason"] = reason or f"command exited with code {code}"
    seal(root, record, tree, "finished")
    write_manifest(path, record)
    print(f"{rid}: {record['status']}; exit {code}; evidence in {run_dir}")
    if record["status"] != "completed":
        print(record["failure_reason"])
    return 0 if record["status"] == "completed" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id")
    parser.add_argument("--project", default=".")
    parser.add_argument(
        "--metrics", default="metrics.json", help="run-relative metrics output file"
    )
    parser.add_argument(
        "--artifact", action="append", default=[], help="additional run-relative output; repeatable"
    )
    parser.add_argument("--timeout", type=float)
    args = parser.parse_args(argv)
    if args.timeout is not None and (not math.isfinite(args.timeout) or args.timeout <= 0):
        parser.error("--timeout must be positive")
    return execute(Path(args.project).resolve(), args.id, args.metrics, args.artifact, args.timeout)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"drf run: {exc}")
