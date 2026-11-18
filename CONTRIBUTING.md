# Contributing to DevResearchFlow

Contributions that make research evidence easier to inspect, preserve, and reproduce
are welcome. Small documentation fixes, reproducible bug reports, and tests for
workflow failures are useful starting points.

## Propose a change

Use a [bug report or feature request](https://github.com/Shakthi-Bala/DevResearchFlow/issues/new/choose).
Include the toolkit version, the command you ran, expected behavior, and a minimal
reproduction. Use synthetic records and remove private data, credentials, unpublished
results, and identifying logs before sharing them. For a substantial workflow or
schema change, open an issue first so the compatibility and scientific implications
can be discussed. Follow [SECURITY.md](SECURITY.md) for sensitive findings.

## Set up locally

Use Python 3.10+ and Git on Linux, macOS, or WSL. From a fork or source checkout:

```bash
git switch dev
git switch -c fix/describe-the-change
python3 -m venv .venv-research
source .venv-research/bin/activate
python -m pip install -e '.[dev]'
```

Open pull requests against **`dev`**. Keep changes focused and describe the concrete
before/after behavior. Tests use isolated local projects and synthetic fixtures;
normal validation requires no paid model calls or real thesis data.

## Validate

Run checks appropriate to your change. For code and workflow changes, use the same
commands as CI:

```bash
python -m unittest discover -s workflows/research/tests -v
ruff check .
ruff format --check . bin/research-init
mypy
python scripts/render_record_states.py --check
bash -n install.sh bin/graphify-init workflows/research/integrations/pre-commit
git diff --check
```

For packaging changes, also run `python -m build` and smoke-test the wheel in a
separate environment outside the checkout. CI tests Python 3.10 and 3.13 on Linux,
and Python 3.13 on macOS; it also collects subprocess coverage and tests the wheel.
See [the workflow](.github/workflows/test.yml) for the current matrix.

If you change lifecycle transitions, regenerate their documentation with
`python scripts/render_record_states.py`. The [toy example](examples/toy-ablation/README.md)
exercises a full evidence trail, including a failed run and a stale review.

## Preserve the research contract

- Keep terminal run evidence and superseded reviews; use new records for retries or corrections.
- Keep structural validation separate from scientific approval. Never label fixture reviews as independent review.
- Preserve customized project files during initialization and updates; test migration and compatibility effects.
- Keep execution evidence and review prerequisites enforced through the CLI, staged hook, and CI paths.
- Add a regression test for a changed behavior when it protects a meaningful workflow property.

Update relevant guides and the **Unreleased** section of [CHANGELOG.md](CHANGELOG.md).
Describe checks actually run and any limits in the pull request. Screenshots or
sample output help when changing the user-facing workflow; sanitize them first.

Contributions are provided under the repository's [MIT license](LICENSE).
