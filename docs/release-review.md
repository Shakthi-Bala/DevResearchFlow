# Release validation summary

Review date: 2026-10-24

This document summarizes the validation performed for the public release of
DevResearchFlow and the scope of those checks.

## Validation results

- **Regression tests:** All 52 tests passed in isolated Linux environments on
  Python 3.10 and 3.13. Additional testing with symlinked temporary directories
  verified the path-alias behavior used by macOS test fixtures.
- **Graphify integration:** The pinned Graphify 0.9.95 CLI extracted a sample
  code graph and generated its HTML visualization and report without an LLM call.
- **Dependency audit:** `pip-audit` reported no known vulnerabilities in the
  resolved validation requirements or the installed optional Graphify dependency
  environment at the time of review.
- **Credential screening:** A scan of 59 historical Git blobs found no matches
  for the five credential patterns checked: private keys, GitHub tokens, provider
  keys, AWS key IDs, and credential-bearing HTTP URLs. No tracked environment
  or private-key filenames were found.
- **Repository checks:** Local Markdown links, heading anchors, code fences,
  JSON schemas, SVG syntax, Python syntax, shell syntax, and Git whitespace
  checks passed.

## Verification scope

These results describe the repository and dependency versions available on the
review date. GitHub-hosted CI results require separate confirmation, including
macOS, which was unavailable in the local review environment.

Optional assistant integrations were tested using isolated command stubs.
The review did not include live model sessions or substantial research experiments.

Credential screening and dependency audits identify known patterns and reported
vulnerabilities; they do not constitute a security certification. Scientific
conclusions require review of the underlying sources, implementation, and run
evidence in addition to structural validation.

## Usability follow-up

The follow-up on 2026-10-24 passed all **63 local regression tests on Python 3.13.5**.
Coverage now includes optional-format-package absence, record helper safety,
staged-tree validation, an actual rejecting pre-commit hook, staged artifact
corruption, and a complete generated example with per-commit history checks.
Shell syntax, local documentation links, and whitespace checks also passed.
These local results do not confirm the subsequent GitHub-hosted CI runs.

The example executes real local commands but labels every scripted review as a
synthetic fixture. A real thesis pilot remains future work. A separate lite policy
is deferred pending experience; existing exploratory mode retains review gates.
