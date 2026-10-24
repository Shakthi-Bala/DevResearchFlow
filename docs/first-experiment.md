# Your first experiment

This ten-step path works with an agent that can read Markdown and run commands.
Load the contracts through Claude Code, Codex, Synaps or your runtime's own context
mechanism. The toolkit does not assume a model name or delegate automatically.
Replace all uppercase placeholders with your actual values.

1. **Install and initialize.** From the toolkit checkout, run `uv tool install .`.
   In your project run `git init`, then `drf init . --ci`. Read `drf status`.
   Use `--no-hooks` only if you intentionally want manual acceptance checks.

2. **Agree the brief.** Load `.research-toolkit/agents/coordinator.md` and ask:

   > Read research/WORKFLOW.md and the brief. Help me bound QUESTION to an observable
   > outcome. My data, hardware and deadline are LIMITS; my compute/token budget is
   > BUDGET. Record the plan and acceptance criteria before substantial execution.

   Complete the starter question, brief and state; commit them. A generated draft
   is not PI approval. For your thesis pilot, record actual decisions explicitly.

3. **Create a hypothesis.** Ask the literature and hypothesis roles:

   > Inspect primary evidence. Separate author claims from reproduced findings.
   > Record alternatives, assumptions and a concrete observation that would falsify
   > the hypothesis. Include conflicting sources and unavailable evidence.

   Use `drf new hypothesis HYP-001 --model MODEL --session SESSION`. Fill its fields
   and link actual source notes. Do not invent literature for a synthetic experiment.

4. **Write the protocol prospectively.** Use
   `drf new experiment EXP-001 --mode confirmatory --model MODEL --session SESSION`.
   Ask methodology:

   > Define baselines, controls, splits, leakage checks, metrics with units,
   > repetitions, seeds, failure criteria, budget and interpretation limits before
   > looking at evaluation outcomes. Link HYP-001 and assign explicit outputs.

   Commit the draft. Use exploratory mode for bounded investigation and a later new
   confirmatory protocol for stronger conclusions.

5. **Get an independent protocol review.** In a fresh context, preferably another
   model, load the verifier contract and ask:

   > Inspect the question and protocol before author summaries. Find a concrete
   > reason this design could be wrong. Check leakage, baselines, measurements and
   > budget. Record actual checks, blocking findings, limits and disposition.

   Prepare hashes with `drf review REV-001 --type protocol --model REVIEW_MODEL
   --session FRESH_SESSION research/experiments/EXP-001.yaml`. Actual review must
   complete it. Link it in the experiment and commit `protocol_reviewed`.

6. **Implement and pin inputs.** Ask the engineer:

   > Implement only the reviewed protocol. Add mathematical/numerical checks. Do
   > not execute the substantial experiment yet. Capture the environment and
   > enumerate every dataset file needed by the run.

   Run `drf dataset-manifest configs/dataset-manifest.json data/`, capture environment
   details in `configs/environment.txt`, and commit implementation/configuration/data
   manifests. Move the experiment to draft if pinning changes are necessary, obtain
   applicable fresh reviews, and use `drf pin research/experiments/EXP-001.yaml`.
   Copy its commit/configuration fields; protocol hashes exclude these pin fields.

7. **Review the implementation.** In a fresh verifier context ask:

   > Check the code against the protocol: equations, shapes, signs, limiting cases,
   > configuration and data flow. Independently recompute key quantities. Return
   > corrections to the engineer; do not fix code you are reviewing.

   Use `drf review REV-002 --type implementation --model REVIEW_MODEL --session
   ANOTHER_SESSION research/experiments/EXP-001.yaml`. Record actual review, link it,
   set `implementation_reviewed`, validate and commit the gate. Confirmatory protocol
   registration must be committed before the runner starts.

8. **Capture a real run.** With actual environment/data files, execute:

   ```bash
   drf prepare-run RUN-001 research/experiments/EXP-001.yaml \
     --environment configs/environment.txt --dataset-version DATA_VERSION \
     --dataset-manifest configs/dataset-manifest.json --device DEVICE --seed 42 \
     --exec python3 src/experiment.py
   git add research runs
   git commit -m 'Prepare reviewed run'
   drf run RUN-001 --timeout 3600
   drf check
   ```

   The program must write `metrics.json` under `DRF_RUN_DIR`. Preserve failed attempts
   and use new IDs for retries. Commit captured evidence. The runner records the
   intermediate start; a valid receipt permits planned-to-terminal Git transitions.

9. **Analyze and challenge the conclusion.** Ask the analyst to reproduce metrics
   from all runs, including failures, and write OBS/CLM drafts with scope and uncertainty.
   Create a confirmatory claim with `drf new claim CLM-001 --mode confirmatory --model
   MODEL --session SESSION`. In a fresh evidence-review context ask:

   > Read raw runs and analysis code before summaries. Recompute critical numbers.
   > Check missing runs, exclusions, uncertainty and contradictory evidence. State
   > what cannot be reproduced and whether the proposed scope is justified.

   Use `drf review REV-003 --type evidence --model REVIEW_MODEL --session
   EVIDENCE_SESSION research/claims/CLM-001.yaml`. Promote only after actual supporting
   review. Add distinct reviews for observations or hypotheses when promoting them.

10. **Record the decision.** Ask the coordinator to report supported, negative or
    inconclusive outcomes with evidence links and the next decision. Write DEC/state,
    run `drf check`, then commit. Require project CI before merging. Never treat a
    passing checker, receipt, or model agreement as a scientific conclusion.

For a tiny executable walkthrough with all records and local history, run the
[runnable example](../examples/toy-ablation/README.md). Its reviews are explicitly
synthetic fixtures, not a substitute for the independent review in steps 5, 7 and 9.
