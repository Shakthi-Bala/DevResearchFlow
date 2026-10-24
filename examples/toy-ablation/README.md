# Runnable toy ablation

This example builds a complete local research project, executes real commands,
and records each workflow gate in Git. It uses strict policy and the real runner
for logs, timestamps, exit codes and execution receipts. It needs Python 3.10+, Git and the toolkit's
validation requirements; it makes no model calls and uses no downloaded dataset.
Run from the toolkit checkout, using a new directory outside the checkout:

```bash
python3 -m venv /tmp/devresearchflow-demo-venv
/tmp/devresearchflow-demo-venv/bin/python -m pip install -r workflows/research/requirements.txt
/tmp/devresearchflow-demo-venv/bin/python examples/toy-ablation/build.py /tmp/my-ablation-demo
```

The destination must not exist. The generator writes and commits only inside that
new directory. Review records are **synthetic teaching fixtures** with explicit
limitations. They demonstrate record structure and links; they are not independent
scientific review or thesis evidence. The demo's local commits use a fictional identity.

The question is whether replacing `2*x` with `x` reduces mean squared error for
`x = [1,2,3,4]`, `y = 2*x`. The baseline has MSE 0; the ablation has MSE 7.5. Thus
the hypothesis that removing the slope helps is contradicted on these four points.
No generalization or statistical significance is claimed.

| Stage | What to inspect in the generated project |
| --- | --- |
| Scope | `research/brief.md`, `research/questions/Q-001.yaml`, `research/hypotheses/HYP-001.yaml` |
| Protocol | `research/experiments/EXP-001.yaml`, `configs/ablation.json` |
| Stale review | Superseded `REV-001`, replacement `REV-002`, and `research/sessions/stale-review.txt` containing the actual rejected validation |
| Implementation | `src/ablation.py`, pinned revision/configuration, fixture `REV-003` |
| Failed execution | `runs/RUN-001/`: actual command, frozen protocol, partial stdout, stderr and nonzero exit |
| Successful execution | `runs/RUN-002/`: metrics, logs and terminal manifest |
| Analysis | `analysis/check.py`, `research/observations/OBS-001.yaml` and analysis output in session notes |
| Interpretation | Scoped `CLM-001`, fixture evidence review `REV-004`, contradicted `HYP-001` and `DEC-001` |

Inspect committed gates and rerun checks:

```bash
cd /tmp/my-ablation-demo
git log --oneline --reverse
/tmp/devresearchflow-demo-venv/bin/python analysis/check.py
/tmp/devresearchflow-demo-venv/bin/python .research-toolkit/checks/validate_records.py . --base-ref HEAD
/tmp/devresearchflow-demo-venv/bin/python .research-toolkit/checks/validate_snapshot.py . --commit HEAD
```

The runner checks the reviewed code and per-file dataset manifest before both
attempts. Confirmatory registration commits and distinct synthetic author/reviewer
identities are recorded. The generator validates every committed snapshot against its parent. The stale
review is rejected before being superseded, and the failed run remains immutable.
The literature and hypothesis stages use the explicitly defined synthetic setup;
there are no external literature claims or invented sources. Task routing and all
review decisions are scripted fixtures, not live multi-agent sessions.
