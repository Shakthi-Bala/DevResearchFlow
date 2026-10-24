# dev_setup

Tools for running research projects with Claude Code:

- **Research workflow:** seven agent roles plan, investigate, implement, review, and analyze your work.
- **Code map:** Graphify helps agents find relevant files, functions, and code relationships.

You provide the research question and budget. The coordinator organizes the work.
Each project keeps its own evidence, experiment results, and decisions.

## 1. Get the toolkit

The research workflow currently lives on the **`dev` branch**. On a new machine:

```bash
git clone --branch dev https://github.com/Shakthi-Bala/dev_setup.git ~/dev_setup
```

If you already have this repository, use your existing checkout.
The examples below assume it is at `~/dev_setup`; replace that path if you cloned
it somewhere else. You need Python 3.10+, Git, and Claude Code available.

## 2. Set up a research project

The examples use `~/my_research_project`. Replace it with your project's folder.

For a **new project**:

```bash
mkdir -p ~/my_research_project
cd ~/my_research_project
git init
```

For an **existing project**, just open its folder:

```bash
cd ~/my_research_project
```

Install the workflow into that project:

```bash
~/dev_setup/bin/research-init .
```

This creates the agent instructions and research folders. It preserves existing
project files and customized agents. It does not start experiments.

Set up the record checker once inside the project:

```bash
python3 -m venv .venv-research
.venv-research/bin/python -m pip install -r .research-toolkit/requirements.txt
```

The checker finds missing fields, broken references, and missing reviews in your
research records.

## 3. Start the coordinator

From your project folder:

```bash
claude --agent coordinator
```

Paste this into the Claude Code conversation, replacing the bracketed parts:

```text
Read research/WORKFLOW.md and research/brief.md. Use all seven agent roles.

My research question is: [what you want to investigate].
My constraints are: [dataset, hardware, deadline, and other limits].
My compute and token budget is: [your limits].

Help me fill in the brief and agree an initial plan before substantial experiments.
Manage the specialist handoffs and the three verifier reviews.
Preserve failed runs, contradictory evidence, and uncertainty.
Commit completed changes. Do not push unless I ask.
```

You do not need to manually start seven sessions. The coordinator calls the
specialists when needed. You control the initial direction, budget, major changes,
and final interpretation.

## 4. Understand the workflow

| Agent | What it does |
| --- | --- |
| Coordinator | Talks with you, makes the plan, assigns work, and tracks progress. |
| Literature researcher | Reads primary sources and records what they actually support. |
| Hypothesis researcher | Suggests explanations, alternatives, and ways to test them. |
| Methodology designer | Defines the experiment, comparisons, measurements, and budget. |
| Engineer | Writes code, runs experiments, and saves execution evidence. |
| Verifier | Independently checks the plan, implementation, and conclusions. |
| Analyst | Computes results, reports uncertainty, and interprets the evidence. |

The work follows this order:

```text
Your question and budget
  → Coordinator makes the plan
  → Literature researcher gathers evidence
  → Hypothesis researcher proposes explanations
  → Methodology designer writes the experiment plan
  → Verifier checks the plan                 [review 1]
  → Engineer implements it
  → Verifier checks the implementation       [review 2]
  → Engineer runs the experiment
  → Analyst analyzes the results
  → Verifier checks the conclusions          [review 3]
  → Coordinator reports the outcome to you
```

If a review finds a problem, the coordinator sends it back for correction.
Negative and inconclusive results are kept too. Passing the record checker means
the records meet its structural checks; the verifier still judges the evidence.

## 5. Find your work and results

These folders belong to **your research project**, not to `dev_setup`:

| Location | What you will find |
| --- | --- |
| `research/brief.md` | Your question, scope, constraints, and budget. Start here. |
| `research/state.yaml` | Current tasks, blockers, and the next decision. |
| `research/sources/` | Paper notes and exact supporting passages. |
| `research/hypotheses/` | Proposed explanations and how to disprove them. |
| `research/experiments/` | Experiment plans written before execution. |
| `runs/` | Actual commands, settings, logs, outputs, and run status. |
| `research/observations/` | Measurements from runs. |
| `research/claims/` | Interpretations linked to supporting and contradicting evidence. |
| `research/reviews/` | What the verifier checked and what remains uncertain. |
| `research/decisions/` | Decisions and the reasons behind them. |
| `.claude/agents/` | The seven project-local agent definitions. |
| `.research-toolkit/` | Templates and record-checking tools. |
| `graphify-out/` | The generated code map, if you enable Graphify. |

**Research records store scientific evidence. Graphify maps the code.**
Agents connect them using file paths, function names, and Git revisions.

## 6. Continue work later

Open your project and start the coordinator again:

```bash
cd ~/my_research_project
claude --agent coordinator
```

For example, ask:

> Read the brief, current state, and recent decisions. Summarize where we are,
> identify blockers, and continue within the agreed plan and budget.

To check the records yourself, run this from the project folder:

```bash
.venv-research/bin/python .research-toolkit/checks/validate_records.py .
```

To also compare status changes and saved run records against the latest Git commit:

```bash
.venv-research/bin/python .research-toolkit/checks/validate_records.py . --base-ref HEAD
```

The agents are instructed to use the reviews and check commands. These are
workflow instructions and manual checks; an always-running service does not enforce them.

## 7. Add the Graphify code map (optional)

Run the machine installer once:

```bash
cd ~/dev_setup
./install.sh
export PATH="$HOME/.local/bin:$PATH"
```

It installs `uv`, the pinned Graphify CLI, its Claude Code skill, and shortcuts
for `graphify-init` and `research-init`. Claude Code itself is installed separately.

Then, inside your project:

```bash
cd ~/my_research_project
graphify-init
```

This builds the code map, adds Claude Code integration, and installs Git hooks
that refresh the map. The default extraction is code-only and runs locally.

Optionally, run `/graphify .` **inside Claude Code** to add document concepts and
community names. This extra step uses session tokens.

Useful terminal commands:

```bash
graphify query "how does data loading work"
graphify explain "SomeClass"
graphify update .
```

After the machine installer, you can also set up both tools together:

```bash
research-init ~/my_research_project --graphify
```

## 8. Update the toolkit and your projects

Update the toolkit checkout:

```bash
cd ~/dev_setup
git switch dev
git pull --ff-only
```

Refresh an existing project's copied workflow files:

```bash
./bin/research-init ~/my_research_project --update
```

This updates unchanged toolkit files and preserves local customizations and
research records. Review the changes and commit them in the project.
Run `./install.sh` again if you also want to refresh the machine's Graphify setup.

## Diagrams and detailed instructions

- [Research workflow](01_research_workflow.svg)
- [Reusable toolkit folders](02_dev_setup_folders.svg)
- [Per-project folders](03_project_folders.svg)
- [Research memory and Graphify](04_memory_and_graphify.svg)
- [Detailed operating guide](workflows/research/README.md): record formats, review rules, provenance, and validation.
