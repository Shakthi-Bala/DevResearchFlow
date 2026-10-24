# Provenance, trust and migration

## What the runner establishes

`drf run RUN-NNN` executes the planned argument list without a shell. It checks
current reviews, frozen input checksums, code/configuration against the reviewed
Git commit and the dataset manifest's actual files. It captures process output,
timestamps, exit code and declared output hashes, then finalizes a receipt-linked
manifest. It refuses patches, changed code, untracked non-record inputs, stale
reviews, reused run IDs and pre-existing output/log files.

A captured failed run can have exit code zero when a required output is missing
or inputs changed during execution. The reason is retained. Timeout and cancellation
preserve logs and available artifacts. Force-kill/host failure may leave an unfinished
started record; retain it and the lock rather than reusing the run ID.

Receipts bind the exact manifest and declared evidence, including stdout/stderr.
Validation rejects missing receipts under strict policy and detects ordinary edits.
A receipt is **not a signature or independent attestation**: an actor controlling the
repository, tool, executable, environment and receipts can forge or replace them all.
Ignored environments, external programs, remote inputs, mutable external services,
and coordinated modifications between checks are outside this local trust boundary.
Use isolated infrastructure, restricted credentials and independently retained CI
artifacts/signed attestations if your threat model includes a hostile repository owner.
No such external signing service is configured by this toolkit.

## Checkable reviewer separation

Record authors use `author: {role, model, session}`; experiment implementations
also record `implementation.author` so a code author cannot review their own work. Reviews use
`reviewer: {role: verifier, model, session}`. Use actual runtime model/session IDs,
not labels that imply independence without evidence. Completed strict reviews require
complete identities and reject the same author/reviewer session, even if model names
differ. Another model in a fresh context is recommended. Identity metadata is
self-reported; it does not prove the author or reviewer is independent.

Inspect specifications, code and raw artifacts before author summaries, and
independently reproduce critical numbers. Preserve failed checks and disagreements.
The runnable example's identities and reviews are labeled synthetic fixtures.

## Confirmatory protocol registration

A `mode: confirmatory` protocol must have a matching version/content hash in an
ancestor Git commit before the runner starts. The runner records that registration
commit; validation checks ancestry, content and its timestamp relative to execution.
Confirmatory supported claims must cite observations/runs from registered confirmatory
experiments. An explicitly exploratory claim cannot become provisionally supported.
Use a new prospectively defined confirmatory protocol and a new claim instead.

Git history demonstrates the recorded ordering, not the absence of unrecorded prior
experiments. Commit dates are mutable; this is not an externally timestamped registry.
A thesis may need preregistration with a trusted independent service as well.

## Policy and migrations

New projects have `research/policy.json` with format 2, `execution_receipts: true`
and `review_identity: true`. Projects with no policy retain legacy behavior; updating
an existing installation creates an explicit legacy policy rather than silently
invalidating old scientific records. `drf status` displays the active policy.

`drf init . --update` refreshes unchanged toolkit files and preserves customizations.
`drf migrate --check` previews a metadata v1→v2 upgrade; `drf migrate` writes it with
backups under `.research-toolkit/migrations/`. Scientific records, review hashes and
terminal run evidence are never rewritten by the migration. The current schemas
accept old records and optional new fields; no historical identity is invented.

`drf migrate --strict` refuses to enable strict policy if historical evidence lacks
actual identities or receipts. Keep legacy policy for that history, or start a new
strict project. Unsupported future format versions fail clearly. Metadata version
and per-record `version` serve different purposes: the former describes installation
metadata, while the latter tracks a scientific record's own revisions.

## Require checks before merging

`drf init . --ci` creates a project workflow named **Research records** with job
**validate**. In GitHub repository settings, configure a branch ruleset/protection
rule for your target branch, require a pull request and require the actual `validate`
status check after its first successful run. Restrict bypass rights as appropriate.
Use the status name shown by GitHub rather than guessing it from the filename.

The toolkit's own CI job names include the OS/Python matrix; select those checks
when protecting this toolkit repository. Local hooks remain bypassable and must be
installed in every clone. These instructions do not change remote repository settings.
See [GitHub's protected-branch documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

A passing CI check validates recorded structure and provenance. Independent review
and the principal investigator still assess the scientific conclusion.
