# Changelog

## Unreleased

- Allow exact validation and verification-test commands in the Claude verifier
  profile; document the trust boundary of Python execution.
- Ignore generated machine-local permission profiles during initialization/update.
- Capture interpreter, packages, GPU/driver and selected environment variables in
  receipt-covered run artifacts, including failed and cancelled executions.
- Add checked `drf advance EXP-NNN STATUS --review REV-NNN` and draft `pin --write`.
- Derive status guidance from linked runs, observations, evidence reviews and decisions.
- Make checkout CLI tests use `src/`; extend mypy to validator and record helper.

## 0.3.0

- Package the toolkit as `drf`, installable from a checkout or built wheel using
  uv, pipx or pip. Record the toolkit version in installation metadata.
- Execute planned runs with reviewed-code checks, real process evidence,
  timeout/cancellation handling and checksummed execution receipts.
- Verify per-file dataset manifests, reviewer sessions and confirmatory protocol
  registration; report actionable gate status.
- Enable hooks by default for Git projects, preserving existing hooks and an
  explicit `--no-hooks` opt-out.
- Fix starter-record recreation on repeat initialization, including renamed Q-001.
- Generate opt-in Codex and Claude role-permission profiles. Add a ten-step
  tutorial, state diagrams and migration/branch-protection guidance.
- Format Python sources with Ruff; check new typed runtime modules with mypy.
  Add property tests, process-level integration tests, coverage and wheel checks.
- Migrate metadata v1 to v2 with backups without rewriting scientific history.
  Existing projects retain legacy policy; new projects use strict policy.

The thesis case study and pilot-driven exploratory tier remain pending. Runtime
profiles have local generation/guard tests; live model sessions are not part of
release validation. Execution receipts are not signed attestations.
