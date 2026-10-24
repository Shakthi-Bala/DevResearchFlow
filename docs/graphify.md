# Optional Graphify code navigation

Graphify provides a code-navigation CLI that any agent with terminal access can
use. The machine installer installs `uv`, the pinned Graphify CLI, and command
shortcuts. Assistant-specific integrations are opt-in; see `./install.sh --help`.

```bash
cd ~/DevResearchFlow
./install.sh
export PATH="$HOME/.local/bin:$PATH"
```

Build and query the code map from your project with the CLI:

```bash
cd ~/my_research_project
graphify extract . --code-only
graphify cluster-only . --no-label
graphify query "how does data loading work"
graphify explain "SomeClass"
graphify update .
```

Code-only extraction runs locally. Ask your agent to use the CLI for navigation
and inspect the underlying source before making correctness claims. The
convenience setup scripts also offer assistant-specific integrations; those are
separate from the shared research process and Graphify CLI.


Run installation only when you want code indexing. The research initializer, records,
helpers, tests and validation work without Graphify or uv. The installer downloads
uv when it is unavailable; inspect `install.sh` before running it.
