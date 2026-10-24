# Record helpers and automatic validation

Run commands from your initialized project root with the validation environment:

```bash
python3 -m venv .venv-research
.venv-research/bin/python -m pip install -r .research-toolkit/requirements.txt
```

The helper is copied into each project. Use `--help` for all options:

```bash
.venv-research/bin/python .research-toolkit/checks/record_helper.py --help
.venv-research/bin/python .research-toolkit/checks/record_helper.py new hypothesis HYP-001
.venv-research/bin/python .research-toolkit/checks/record_helper.py new experiment EXP-001
```

Replace draft placeholders and assign actual scope. Commands create new files exclusively;
they refuse existing files and symlinked destinations. Creation is not approval.
For an initial question, edit the existing `research/questions/Q-001.md` rather than
creating another record with the same ID.

## Review hashes and implementation fields

Prepare a pending review with computed target hashes:

```bash
.venv-research/bin/python .research-toolkit/checks/record_helper.py review REV-001 \
  --type protocol research/experiments/EXP-001.yaml
```

An independent verifier must perform and record the checks, findings, limitations
and disposition before completing it. The helper does not change experiment status,
review links, or scientific acceptance. After a target changes, supersede its old
review and create a new review ID; do not refresh a completed review's hashes.

Commit implementation and configuration, then print fields for the draft experiment:

```bash
.venv-research/bin/python .research-toolkit/checks/record_helper.py pin \
  research/experiments/EXP-001.yaml
```

Copy these fields into the draft before obtaining applicable reviews. `pin` refuses
uncommitted implementation/config changes and does not modify records. Pinning is
bookkeeping, not proof of which code will execute.

## Prepare a run without executing it

Once the experiment has supporting protocol and implementation reviews and its
status is `implementation_reviewed`, capture a planned run:

```bash
.venv-research/bin/python .research-toolkit/checks/record_helper.py prepare-run RUN-001 \
  research/experiments/EXP-001.yaml \
  --environment configs/environment.txt \
  --dataset-version dataset-v1 --dataset-manifest configs/dataset-manifest.json \
  --device CPU --seed 42 --exec python3 src/experiment.py
```

Provide real environment and dataset captures first. The helper copies the reviewed
configuration and protocol, hashes those files and the environment/dataset manifest,
and fills review links, commit, patch and command. It creates no logs or results and
does not run the command. Review the planned record before execution.

At actual start, create log files, record `started_at` and set `status: started`.
Persist actual output immediately, even on failure, and fill the finish timestamp,
exit code, status, failure reason, metrics and artifacts. Commit intermediate states
before later transitions. Never rewrite a terminal manifest; start a fresh run.

Print an artifact mapping without modifying any record:

```bash
.venv-research/bin/python .research-toolkit/checks/record_helper.py artifact runs/RUN-001/metrics.json
```

## Optional pre-commit hook and CI

From the toolkit checkout, opt into either or both integrations:

```bash
./bin/research-init /path/to/project --hooks --ci
```

The project must already be a Git repository rooted at that path for `--hooks`.
The initializer honors `core.hooksPath` and preserves any existing pre-commit hook.
To integrate with an existing hook, call the command below from your hook; the
sample is available in `.research-toolkit/integrations/pre-commit`.
Existing `.github/workflows/research-records.yml` files are also preserved.

```bash
.venv-research/bin/python .research-toolkit/checks/validate_snapshot.py . --staged
```

The hook validates an isolated copy of the index, including staged artifacts and
configuration, and compares statuses and run history against HEAD. Unstaged files
cannot hide staged errors or supply missing evidence. An initial commit is checked
structurally without a historical baseline. Exported Git symlinks, submodules and
unmerged entries are rejected explicitly; use manual validation for projects that
require these layouts. Large tracked artifacts increase snapshot cost.

Project CI checks each pushed/PR commit against its own first parent. It avoids
comparing the final result directly to a much older branch base, which would falsely
report skipped gates when intermediate gates were committed. On a new branch it
checks the tip against its parent. Projects enabling CI midway through existing
history should start after the initialization commit. CI runs the installed version
of the checker from the selected head; it is not a tamper-proof trust boundary.

```bash
.venv-research/bin/python .research-toolkit/checks/validate_snapshot.py . --commit HEAD
```

Local hooks are bypassable and need installation in each clone. Configure required
CI checks through your hosting service if you need merge enforcement. Neither
integration controls execution or substitutes for scientific review.

## Exploration

For now, use `mode: exploratory` and bound the question and resource budget. Helpers
reduce paperwork while keeping the existing review gates. A separate lite policy is
deferred until real usage shows which records can safely be omitted. Exploratory
results require a new prospectively defined confirmatory protocol before stronger claims.
