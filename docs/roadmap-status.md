# Roadmap implementation status

## Implemented for 0.3.0

| Roadmap item | Implementation and practical limit |
| --- | --- |
| Execute runs | `drf run` checks reviewed inputs, executes the process and captures evidence/receipts. Strict validation requires receipts; they are not signed attestations. |
| Q-001 recreation | Starter records are created only on first installation. Reinitializing the completed example with hooks has a regression test. |
| Unified CLI | Installable wheel/sdist with `drf init/new/review/run/check/status`, plus pinning, datasets, migration and permission helpers. No PyPI publishing was performed. |
| Reviewer identities | Root author and implementation author identities; completed strict reviews reject matching sessions. Self-reported metadata cannot prove independence. |
| Preregistration | Confirmatory runs record matching ancestral protocol commits before start; supported strict claims need registered confirmatory evidence. Git dates are not trusted third-party timestamps. |
| Dataset contents | Per-file hashes/sizes and input roots detect changed, added or removed dataset files. |
| Default hooks | Enabled for root Git projects; opt out with `--no-hooks`. Existing/external hooks remain protected. |
| Role permissions | Opt-in Codex profiles and restrictive Claude file-tool guards are generated and locally tested. Live runtime activation/verification remains an operator step; no model sessions were launched. |
| Learnability | Short README, ten-step tutorial, runner-backed example, lifecycle diagrams and branch-protection guidance. |
| Code quality | Ruff formatting/lint, typed CLI/provenance/runner checked by mypy, property tests, coverage reporting, source/wheel build and wheel smoke checks in CI. This is not full static typing of every legacy helper. |
| Versions/migration | Versioned package/metadata and changelog; backed-up metadata v1→v2 migration preserves scientific records and legacy policy. Unsupported future formats fail rather than guessing a conversion. |

## Intentionally pending

- **Real thesis case study:** deferred to the user's project, with real independent
  review and publishable evidence rather than synthetic fixtures.
- **Simplified exploratory tier:** design it from pilot observations. Current
  exploratory experiments retain review gates, and exploratory claims cannot be
  promoted directly to confirmatory support.
- **A measured usability score:** no claim of 9/10 or sub-20% overhead is made
  without pilot evidence. Record research/record/review time and token counts
  consistently during the thesis pilot; retain failure/rework costs as well.
- **External trust infrastructure:** signed/remote attestations, immutable external
  storage and institution-approved preregistration are deployment choices, not
  claims made by local checksums or self-reported agent identities.

Remote branch protection is documented but is not changed automatically. Runtime
profiles are never silently applied to a user's existing agent configuration.
