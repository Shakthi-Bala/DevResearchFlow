# Security policy

## Reporting a vulnerability

For vulnerabilities involving code execution, path traversal, unintended writes,
credential exposure, or bypasses of documented validation boundaries, use GitHub's
[private vulnerability reporting](https://github.com/Shakthi-Bala/DevResearchFlow/security/advisories/new)
when available. If private reporting is unavailable, contact the maintainer through
[their GitHub profile](https://github.com/Shakthi-Bala) to arrange a private channel
before sharing sensitive details. Do not include exploit details or private research
data in a public issue.

Include the affected commit or tag, environment, minimal reproduction, expected
boundary, observed behavior, and impact. Use synthetic data whenever possible.
No response-time or coordinated-disclosure deadline is guaranteed.

## Versions and fixes

Security fixes are developed on `dev`. Check [tags](https://github.com/Shakthi-Bala/DevResearchFlow/tags)
and [the changelog](CHANGELOG.md) for published versions and subsequent fixes.
There is no separate long-term-support branch or guaranteed backport policy.

## Trust boundaries

DevResearchFlow executes project-supplied commands. Run only code you trust, or
use an external OS sandbox/container appropriate to the project. Generated agent
profiles are opt-in controls and require verification in the actual runtime;
Python verification tests can perform writes outside file-tool guards.

Execution receipts are local integrity checks, not signed attestations against
someone controlling the repository, checker, or host. Reviewer identities are
self-reported. Validation does not prove scientific correctness. See
[provenance](docs/provenance.md) and [role permissions](docs/permissions.md) for details.
