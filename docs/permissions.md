# Optional role permissions

Generate a profile for a dedicated role session:

```bash
drf permissions --runtime codex --role verifier
drf permissions --runtime claude --role verifier
```

The files are created exclusively under `.research-toolkit/permissions/`. Existing
runtime settings and user/home configuration are never changed. Choose among all
seven roles; verifier writes are confined to `research/reviews/` and
`tests/verification/`. Engineer writes exclude reviews and verification tests.
The supplied areas are conservative: assign shared claims explicitly through the
coordinator instead of widening a specialist's permissions implicitly.

## Codex

Review the generated TOML and merge it into a dedicated trusted Codex configuration.
It selects a named `drf_verifier` permissions profile, extends `:read-only`, grants
writes only to the listed absolute directories, disables network access and uses
`approval_policy = "never"` to avoid escalating past the role boundary.

Do not combine `default_permissions` with `sandbox_mode` or
`[sandbox_workspace_write]`. Paths are specific to that checkout; regenerate for a
new location. Use a runtime supporting named permission profiles; fail rather than
falling back to broad workspace writes if a version rejects the configuration.
An administrator can manage permitted profiles for stronger enforcement.

The generated TOML is syntax-tested locally. No live Codex session or OS sandbox
escape test is included in this release's validation. Confirm the effective profile
in the runtime and try an allowed review write and a denied source write before
relying on it. Connected apps/MCP tools are separate capabilities; remove write-capable
connectors or enforce matching restrictions at their service boundary.

Sources: [official OpenAI configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

## Claude Code

Review the generated JSON and load it as settings for a dedicated role session.
It uses `Edit(path)` rules (which cover built-in file writers), a `PreToolUse` guard,
and `dontAsk`. The guard permits known read tools and built-in file writes only
within that role's paths. It denies shell execution, delegation and unknown tools;
MCP and PowerShell are denied as well. This prevents a shell/Python call from
bypassing file-tool rules. The profile deliberately cannot run experiments: use
`drf run` from a separate trusted terminal/engineer workflow.

Do not run this session with bypass-permissions mode or broaden its tools behind
the guard. Use managed settings when the operator must not override policy. The
profile protects runtime tool calls while enabled; it is not a host filesystem
sandbox against arbitrary processes launched by someone else.

The guard has tests for allowed review writes, denied implementation writes,
shell calls, unknown tools and symlink destinations. Live Claude sessions are not
part of local release validation. Check the runtime's loaded settings and actual
tool names; unsupported/new tools are denied until explicitly evaluated.

Source: [Claude Code permissions](https://code.claude.com/docs/en/permissions).

## Boundaries

These are opt-in runtime-specific profiles, not changes to the common role prompts.
They are not activated by merely loading a role contract. Generated files preserve
existing settings and require deliberate runtime activation. Process/connector
permissions and the user's authority remain separate from the toolkit's ownership
rules. The coordinator remains the single Git writer unless explicitly delegated.
