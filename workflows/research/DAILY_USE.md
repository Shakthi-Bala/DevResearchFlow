# Daily commands

Install `drf` from the toolkit checkout with `uv tool install .`, `pipx install .`,
or `python3 -m pip install .`. `drf --project /path/to/project COMMAND` selects
another project; put global `--project` before the command. `drf COMMAND --help`
shows the command's options. Project commands use its installed, versioned checks.

## Initialize and update

```bash
git init
drf init . --ci
drf status
```

New projects require execution receipts and completed review identities. A Git
pre-commit hook is installed by default; `--no-hooks` opts out. Existing hooks,
external/disabled hooksPath settings, CI files and customized toolkit files are
preserved. Explicit `--hooks` opts into installing at a configured external hook
path. Default setup never modifies your global runtime configuration.

```bash
drf init . --update
drf migrate --check
drf migrate
```

Updates preserve scientific records and legacy project policy. Metadata migration
creates backups; it never fabricates historical receipts or reviewer identities.
`drf migrate --strict` enables strict policy only when existing evidence already
satisfies it. Use a new strict project when historical manual runs cannot qualify.
Starter brief/state/Q-001 files are created only on the first installation.

## Drafts and review hashes

```bash
drf new hypothesis HYP-001 --model ACTUAL_MODEL --session ACTUAL_SESSION
drf new experiment EXP-001 --mode confirmatory --model ACTUAL_MODEL --session ACTUAL_SESSION
drf review REV-001 --type protocol --model REVIEW_MODEL --session FRESH_SESSION \
  research/experiments/EXP-001.yaml
```

Fill every placeholder and record actual identities. Helpers never approve a
review or promote a scientific result. An independent reviewer must fill its actual
checks, findings, limits and disposition before setting `status: completed`.
For code reviews, fill `implementation.author` with the actual engineer identity too.
The same author/reviewer session is rejected even if the model label differs.
Using another model and a fresh context is recommended; identity fields remain
self-reported metadata rather than authentication.

After changing a target, replace its review rather than refreshing completed hashes:

```bash
drf review REV-002 --type protocol --supersedes REV-001 \
  --model REVIEW_MODEL --session ANOTHER_SESSION research/experiments/EXP-001.yaml
```

This creates a pending replacement, marks the original superseded, and retains its
findings/narrative. Update the experiment's required review link after actual review.
Commit intermediate gates so Git history retains each transition.

Commit reviewed implementation/configuration, then print the pinning fields:

```bash
drf pin research/experiments/EXP-001.yaml
```

Copy the fields into the draft before applicable reviews. Pinning refuses dirty
implementation/configuration and does not edit the record. The runner requires
fully committed code without an uncommitted patch.

## Dataset manifests

```bash
drf dataset-manifest configs/dataset-manifest.json data/
```

The output must be outside its inputs. The helper hashes every file, records sizes,
and retains input roots. Verification detects added/deleted/changed files and rejects
symlinks. Manifests may describe explicitly selected files instead of entire folders.
Hashing large datasets costs I/O; a manifest identifies the files, not scientific validity.

## Prepare and execute

With current supporting protocol and implementation reviews, prepare a new run:

```bash
drf prepare-run RUN-001 research/experiments/EXP-001.yaml \
  --environment configs/environment.txt \
  --dataset-version dataset-v1 --dataset-manifest configs/dataset-manifest.json \
  --device CPU --seed 42 --exec python3 src/experiment.py
git add research runs
git commit -m 'Prepare reviewed execution'
drf run RUN-001 --timeout 3600 --artifact predictions.json
```

Capture the actual environment before planning. The program should write metrics
and declared artifacts inside the directory given by `DRF_RUN_DIR`. It may also use
`{run_dir}` in planned command arguments; the runner expands it to `runs/RUN-001`.
The default metrics file is `metrics.json`; change it with `--metrics filename`.
`--artifact` is repeatable and declares additional run-relative outputs.

The runner checks current reviews, frozen protocol/config/environment checksums,
tracked non-record inputs against the reviewed commit, staged/untracked non-record
changes, per-file dataset contents and confirmatory Git registration before launch.
Research records, run evidence and the installed toolkit are excluded from the code
tree comparison. Ignored environments and external tools are not hermetically pinned.
Use explicit absolute interpreter paths when environment selection matters.

The runner captures stdout/stderr, start/finish times, real exit code, outputs and
checksums; atomically finalizes the manifest and writes execution receipts. Timeouts,
launch failures and interruption retain available evidence. A zero-exit command with
missing declared outputs is recorded as failed. Terminal records cannot be rerun.
Use a fresh run ID after a failure; never delete its evidence to reuse the directory.
If the host crashes or the runner is forcibly killed, retain the started record,
lock and partial logs; report the interrupted attempt and start a new run. Do not
invent a terminal receipt for it.

```bash
drf artifact runs/RUN-001/metrics.json
drf status
drf check
git add research runs
git commit -m 'Preserve captured execution'
```

Receipts are checksummed local evidence, not signed attestation against a repository
owner. Confirmatory supported claims must declare `mode: confirmatory` and cite
run-backed preregistered evidence. Exploratory claims cannot be promoted directly;
define a new prospective protocol and claim.

## Hooks and project CI

```bash
drf check --staged
drf check --commit HEAD
drf check --base-ref HEAD
```

The hook checks an isolated index snapshot, so working-file repairs cannot hide
staged errors or supply unstaged evidence. Existing hooks can call `drf check --staged`
or use `.research-toolkit/integrations/pre-commit`. Symlinks, submodules and conflicts
in exported snapshots are rejected explicitly. Large tracked artifacts increase cost.

Project CI checks committed transitions against each commit's own first parent,
including valid planned-to-terminal runner receipts. On a newly pushed branch it
checks the tip and its parent. Enable CI after workflow initialization when adopting
it into existing history. CI uses the installed head checker, not an independent
attestation authority. Require its `validate` job through your hosting settings.

## Compatibility and exploration

The `bin/research-init` entry point and project-local Python scripts still work.
Their helpers are the same implementation exposed by `drf`. Existing project policy
is retained on update; `--legacy` explicitly selects legacy policy for a first install.

Use bounded `mode: exploratory` experiments today. A separate simplified tier remains
deferred until thesis-pilot evidence identifies fields that can safely be omitted.
