# dev_setup

One-command setup for AI-assisted coding: Graphify code graphs, Claude Code config and agentic workflows on any machine.

## Quick start

```bash
# once per machine
git clone https://github.com/Shakthi-Bala/dev_setup.git ~/dev_setup && ~/dev_setup/install.sh

# once per project
cd ~/any_project && graphify-init
# then, in Claude Code inside that project:
/graphify .
```

## What's inside

| Path | What it does |
|---|---|
| `install.sh` | Machine setup: installs [uv](https://github.com/astral-sh/uv), the Graphify CLI (pinned version), the `/graphify` Claude Code skill, and links `bin/*` into `~/.local/bin`. Safe to re-run. |
| `bin/graphify-init` | Per-project setup (see below). |
| `templates/graphifyignore` | Default `.graphifyignore` copied into new projects (data, outputs, envs, third-party code...). |
| `workflows/` | Agentic workflows (coming soon). |

## Graphify: a code map for Claude Code

[Graphify](https://github.com/Graphify-Labs/graphify) parses a repo's syntax trees locally (no API calls) into a knowledge graph of files, classes, functions and how they connect. Claude Code reads the graph instead of grepping through raw files, so codebase questions cost a fraction of the tokens.

`graphify-init` sets up a project in one go:

1. writes `.graphifyignore` and adds `graphify-out/` to `.gitignore`
2. builds the code graph (`graphify-out/graph.json`, `graph.html`, `GRAPH_REPORT.md`)
3. `graphify claude install`: rules in `CLAUDE.md` + a PreToolUse hook so Claude queries the graph before searching files
4. `graphify hook install`: git hooks that rebuild the graph after every commit, checkout and merge

Then run `/graphify .` once in Claude Code: it adds the README/docs concepts and names the graph's communities (uses some session tokens, one time).

Options: `graphify-init [DIR] [--full] [--commit-graph] [--no-claude] [--no-hooks]` (`--help` for details).

Everyday commands:

```bash
graphify query "how does X work"     # scoped subgraph for a question
graphify explain "SomeClass"         # a node and its neighbours
graphify path "A" "B"                # how two things connect
graphify god-nodes                   # most connected code
graphify benchmark                   # tokens saved vs reading raw files
graphify update .                    # refresh after uncommitted edits
```

## Updating

```bash
cd ~/dev_setup && git pull && ./install.sh                  # scripts are symlinked, so pull is enough for them
GRAPHIFY_VERSION=latest ./install.sh                        # move to the newest Graphify release
```

Bump `GRAPHIFY_VERSION` in `install.sh` once a new version is checked, so every machine stays on the same one.
