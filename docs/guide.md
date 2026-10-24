> For current commands, strict policy and execution, start with the [first-experiment tutorial](first-experiment.md) and [daily-use guide](../workflows/research/DAILY_USE.md).

<div align="center">

# DevResearchFlow

### A structured research workflow for any AI agent

Seven agent roles · Three independent review stages · Versioned research evidence

[Quick start](#quick-start) · [Architecture](#architecture) · [Engineering](#engineering-decisions) · [Usage](#everyday-use) · [Detailed guide](../workflows/research/README.md)

</div>

![Animated research workflow: colored outlines follow each active step, with amber highlights for the three verifier reviews](assets/research-workflow.gif)

The outline follows the normal workflow; review findings return work for correction.
[View the static diagram](assets/research-workflow.svg).

`DevResearchFlow` turns a research question into a sequence of defined tasks, reviewed
experiments, and evidence-linked conclusions. A coordinator manages specialist
agents; an independent verifier checks the experiment protocol, implementation,
and final interpretation.

The toolkit combines **reusable agent role contracts**, **Python validation tools**,
**JSON Schema record formats**, and an optional **Graphify code map**. Each research
project retains its own evidence and history. You remain responsible for the
research direction, budget, and final scientific interpretation.

## The problem it addresses

An agent's answer is easier to trust when you can inspect the source, the code,
the command that ran, and the limits of the result. Research also needs a record
of failures, alternative explanations, and evidence that contradicts a conclusion.

This project makes those records part of the workflow:

| Research need | Implemented approach |
| --- | --- |
| Clear responsibilities | Seven role contracts with assigned writing areas and handoff requirements. |
| Review before execution | Separate protocol and implementation reviews before substantial experiments. |
| Traceable conclusions | Claims link to observations, sources, reviews, and explicit scope. |
| Reproducible run records | Frozen protocols, code revisions, configuration hashes, commands, and raw artifacts. |
| Safe reuse across projects | An initializer that preserves customizations and records installed toolkit versions. |
| Detectable record errors | Schema, reference, checksum, review-prerequisite, and Git history checks. |

## Architecture

The reusable toolkit lives in `DevResearchFlow`. Scientific records belong to the
project where the research happens.

```mermaid
flowchart TB
    T["DevResearchFlow toolkit<br/>Agent contracts · Schemas · Templates · Checks"]
    T -->|research-init: versioned copies| P
    subgraph P["Your research project"]
        C["Coordinator<br/>Scope, task ownership, handoffs"]
        S["Specialists<br/>Literature · Hypothesis · Methodology<br/>Engineering · Verification · Analysis"]
        K["Research records<br/>Sources, protocols, observations,<br/>claims, reviews, decisions"]
        R["Run evidence<br/>Commands, configuration, logs,<br/>metrics, artifacts"]
        G["Graphify code map<br/>Files, symbols, relationships"]
        C --> S
        S --> K
        S --> R
        S -->|Locate code, then inspect source| G
        R -->|Supports analysis| K
    end
    K --> V["Python validators<br/>Structure · References · Provenance · Review prerequisites"]
```

**Research records store scientific knowledge; Graphify indexes the implementation.**
Agents connect them through file paths, qualified symbols, and Git revisions.
The generated code graph is a navigation aid; the underlying records and artifacts
remain the evidence to inspect.

## Quick start

Requires **Python 3.10+**, **Git**, and **an AI agent of your choice**. The Bash
setup scripts target Unix-like systems; use WSL on Windows. Role
instructions and research records are reusable across agents; map role loading,
tool access, and delegation to your chosen runtime.

### 1. Get the toolkit

```bash
git clone --branch main https://github.com/Shakthi-Bala/DevResearchFlow.git ~/DevResearchFlow
```

Already cloned it? Use your existing checkout. Replace `~/DevResearchFlow` below with
its actual location if different.

### 2. Prepare your project

For a new project:

```bash
mkdir -p ~/my_research_project
cd ~/my_research_project
git init
```

For an existing project, open its folder instead. Then install the workflow:

```bash
~/DevResearchFlow/bin/research-init .
python3 -m venv .venv-research
.venv-research/bin/python -m pip install -r .research-toolkit/requirements.txt
```

Initialization creates the seven agent definitions, record templates, checking
tools, and initial research brief. Existing files and customized agents are
preserved. Experiments start only after you define the question and agree a plan.

### 3. Give your AI agent the coordinator role

Open your project in your preferred AI agent. Load the coordinator instructions
from `.research-toolkit/agents/coordinator.md` in your project, using your agent's
instruction or context-loading mechanism. The other six role contracts are in
the same folder. Adapt runtime-specific frontmatter and tool names as needed;
the Markdown bodies define the research responsibilities.

Give the coordinator a bounded question and clear limits:

```text
Read research/WORKFLOW.md and research/brief.md. Use all seven agent roles.

Research question: [what you want to investigate]
Constraints: [dataset, hardware, deadline, and other limits]
Compute and token budget: [your limits]

Help me complete the brief and agree an initial plan before substantial experiments.
Manage specialist handoffs and the protocol, implementation, and evidence reviews.
Preserve failed runs, contradictory evidence, and uncertainty.
Commit completed changes. Do not push unless I ask.
```

With delegation support, the coordinator invokes specialists when needed. If your
agent cannot delegate, assign the roles across separate sessions and pass the
versioned task records between them. Keep verification in a fresh reviewer
context, preferably using a different model, and ask it to recompute key numbers
from raw evidence before reading author summaries.

The initializer copies all seven contracts into `.research-toolkit/agents/` and
adds a workflow block to `AGENTS.md`, preserving existing instructions. Load the
contracts through your agent's own instruction system. Additional runtime-specific
integrations are opt-in; inspect `research-init --help` for available options.

## Less bookkeeping in daily use

Try the [runnable worked example](../examples/toy-ablation/README.md): it executes a
small deterministic ablation, preserves an injected failed run, demonstrates stale
review recovery, and ends with a contradicted hypothesis and scoped decision.
Its review records are explicitly synthetic teaching fixtures.

[Record helpers](../workflows/research/DAILY_USE.md) create drafts, calculate review
hashes and artifact checksums, and prepare frozen run provenance. They never approve
reviews or claim execution. `drf init . --ci` installs staged
record validation and a project GitHub Actions workflow while preserving existing files.

## The seven roles

| Role | Responsibility | Main output |
| --- | --- | --- |
| **Coordinator** | Scope the question, assign tasks, route corrections, and report progress. | Brief, task contracts, state, decisions. |
| **Literature researcher** | Read primary sources and separate author claims from reproduced findings. | Source notes with exact passages and limitations. |
| **Hypothesis researcher** | Propose mechanisms, competing explanations, and falsification conditions. | Testable hypotheses and alternatives. |
| **Methodology designer** | Define baselines, controls, metrics, repetitions, and resource limits. | Versioned experiment protocol. |
| **Research engineer** | Implement reviewed protocols, execute experiments, and preserve evidence. | Code, checks, run manifests, logs, artifacts. |
| **Independent verifier** | Challenge the protocol, implementation, and conclusions. | Three distinct review reports with findings and uncertainty. |
| **Results analyst** | Compute measurements and assess uncertainty, failures, and claim scope. | Reproducible analysis, observations, proposed interpretations. |

Corrections return through the coordinator. A negative or inconclusive outcome is
preserved with its evidence and limitations. Agent agreement alone does not count
as scientific support.

## Engineering decisions

| Decision | Why it matters |
| --- | --- |
| **Copy project instructions and record their origin** | A toolkit update does not silently change a project's governing instructions. |
| **One assigned writer per file** | Ownership and handoffs reduce competing edits to shared research records. |
| **Separate observations from claims** | Interpretations can change while the original measurements remain intact. |
| **Pin review targets and artifact checksums** | Changed evidence or protocols can be detected instead of silently reusing a stale review. |
| **Preserve terminal run records** | Optional Git-baseline checks detect modified or deleted execution manifests. |
| **Separate structural and scientific review** | Deterministic tools check records; the verifier assesses whether the evidence supports the conclusion. |

### Verification

The integration suite covers initialization, customization
preservation, stale reviews, broken references, malformed inputs, corrupted
artifacts, run history, installed check commands, and setup-script behavior.

With the validation dependencies available:

```bash
python3 -m unittest discover -s workflows/research/tests -v
```

[Inspect the test suite](../workflows/research/tests) ·
[Inspect the validation tools](../workflows/research/checks)

## Everyday use

Reopen the project in your preferred AI agent, load the coordinator role, and ask:

> Read the brief, current state, and recent decisions. Summarize progress, identify
> blockers, and continue within the agreed plan and budget.

Check its records:

```bash
.venv-research/bin/python .research-toolkit/checks/validate_records.py .
```

Also compare allowed status changes and run history against the latest commit:

```bash
.venv-research/bin/python .research-toolkit/checks/validate_records.py . --base-ref HEAD
```

### Where to find things

```text
my_research_project/
├── AGENTS.md              Shared workflow instructions
├── .research-toolkit/     Role contracts, schemas, templates, and checks
├── research/
│   ├── brief.md           Question, constraints, budget
│   ├── state.yaml         Active work, blockers, next decision
│   ├── sources/           Primary-source notes
│   ├── hypotheses/        Explanations and planned tests
│   ├── experiments/       Protocols defined before execution
│   ├── observations/      Recorded measurements
│   ├── claims/            Scoped interpretations and evidence links
│   ├── reviews/           Independent review findings
│   └── decisions/         Outcomes and their rationale
├── runs/                  Actual execution evidence, including failures
├── src/                   Implementation
├── analysis/              Reproducible analysis scripts
└── graphify-out/          Optional generated code index
```

The source role contracts live in `workflows/research/agents/` in this toolkit;
projects receive versioned copies in `.research-toolkit/agents/`. The initializer
also creates task, question, and session folders, configurations, scripts, and a
verification-test directory. See the [full project layout](../workflows/research/README.md#installed-project-layout).

## Optional code navigation

Research initialization and validation need neither Graphify nor uv. If your project
benefits from a generated code map, see the [optional Graphify guide](graphify.md).

## Update an existing installation

```bash
cd ~/DevResearchFlow
git switch main
git pull --ff-only
./bin/research-init ~/my_research_project --update
~/my_research_project/.venv-research/bin/python -m pip install \
  -r ~/my_research_project/.research-toolkit/requirements.txt
```

Unchanged managed files are refreshed; local customizations and scientific
records are preserved. Review and commit project updates. Rerun `./install.sh`
when you also want to refresh the machine's Graphify setup.

## Current scope

This is a working toolkit of agent instructions and local utilities. The
coordinator follows the workflow in your chosen AI environment; there is no separate
always-running orchestration service or automatic experiment launcher.
Review prerequisites are checked by the validator, which can run manually or through
the optional pre-commit hook and project CI. There is no execution scheduler.
Passing validation establishes structural properties,
not scientific correctness. Reviewers and the principal investigator assess the
substance of the evidence.

For record formats, review dispositions, provenance rules, and reproducibility
details, read the [research operating guide](../workflows/research/README.md).

## Acknowledgements

[Graphify](https://github.com/Graphify-Labs/graphify) provides the optional code
graph and navigation tools used by DevResearchFlow. Thank you to the Graphify
maintainers and contributors for their work.

The research workflow, agent contracts, evidence schemas, and validation utilities
are developed in this repository.

## License

[MIT](../LICENSE). See the [release review](release-review.md) for validation
results and the boundaries of the public-release check.
