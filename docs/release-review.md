# Public-release review

Reviewed: 2026-10-24. This review covers the repository and the local release checks;
it does not change the repository's visibility.

## Findings corrected

| Area | Finding | Correction |
| --- | --- | --- |
| Licensing | No license was present. | Added the maintainer-selected MIT license and included it in installed toolkit copies. |
| Agent portability | Setup defaulted to one runtime despite the reusable role contracts. | Default to project-local `.research-toolkit/agents/` and `AGENTS.md`; runtime-specific integration is opt-in. |
| Input handling | Malformed state and protocol snapshots could raise uncaught exceptions. | Validate YAML and schema before reading fields or following references. |
| Dependencies | Date/time format validation depended on an undeclared optional package. | Declare the JSON Schema format dependencies and test in fresh environments. |
| Record integrity | Implementation-review links and task dependencies could point to the wrong record kind. | Enforce record kinds, review targets, and acyclic task dependencies. |
| Run planning | Unstarted and pre-start-cancelled runs incorrectly required execution artifacts. | Check execution artifacts only after a run actually starts. |
| Installation safety | Tampered installation metadata could reference paths outside the project. | Reject absolute and parent-traversing paths; preserve symlink protections. |
| Setup consistency | Fallback Graphify installation was unpinned; cached directories could become command links. | Use the pinned version and link regular files only. |
| Ignore rules | Graph tracking did not remove the exact generated ignore entry; symlinked ignore files could be modified. | Honor the graph-tracking option and refuse symlinked ignore files. |
| Ongoing verification | Tests ran only through local commands. | Add pinned, read-only GitHub Actions for Linux/Python 3.10 and 3.13, and macOS/Python 3.13. |

## Checks performed

- All 52 regression tests passed in isolated dependency environments on Linux,
  using Python 3.10 and 3.13.
- The actual pinned Graphify 0.9.95 CLI extracted a small code graph and generated
  the HTML graph and report without an LLM call.
- `pip-audit` reported no known vulnerabilities for the resolved validation
  requirements or the installed optional Graphify dependency environment at review time.
- A scan of 59 historical Git blobs found no matches for five high-confidence
  credential patterns: private keys, GitHub tokens, provider keys, AWS key IDs,
  and credential-bearing HTTP URLs. No tracked environment or private-key filenames
  were found. Credential values were not printed or written into this report.
- Local Markdown links, heading anchors, code fences, JSON schemas, SVG syntax,
  Python syntax, shell syntax, and Git whitespace were checked.

## Scope limits

GitHub-hosted CI is configured; its hosted results must be checked after the push,
especially macOS, which was not available in the local environment. No paid model
sessions or substantial research experiments were run during this review.
Optional assistant integrations were tested through isolated command stubs, not
by changing a real user's assistant configuration.

Pattern scans and vulnerability databases can miss issues. These results are
bounded release checks, not a security certification. The workflow's scientific
reviews still require inspecting the underlying sources, code, and run evidence;
a passing structural validator cannot establish scientific correctness.
