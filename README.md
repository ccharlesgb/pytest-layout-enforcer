# pytest-layout-enforcer

`pytest-layout-enforcer` keeps test files structurally aligned with the Python
modules they exercise. It is both a pytest plugin and a standalone command, so
the same invariant can run during test collection, in CI, in pre-commit, or
immediately after an automated refactor.

Given:

```text
src/my_package/
├── core.py
└── services/
    └── billing.py
```

these test paths are valid:

```text
tests/
├── test_core.py
├── test_core_parsing.py
└── services/
    ├── test_billing.py
    └── test_billing_refunds.py
```

## Installation

```console
uv add --dev pytest-layout-enforcer
```

The package uses `uv_build` and can be built locally with:

```console
uv build
```

## Configuration

Add at least one source-to-test mapping to the host project's
`pyproject.toml`:

```toml
[tool.pytest-layout-enforcer]
enabled = true
feature-pattern = "[a-z][a-z0-9_]*"
feature-separator = "_"
require-tests = false
include-init = false

exclude-sources = ["**/_version.py", "**/migrations/**"]
exclude-tests = ["**/test_integration_*.py"]

[[tool.pytest-layout-enforcer.layouts]]
source = "src/my_package"
tests = "tests"
```

For tests stored inside the package, only the test root changes:

```toml
[[tool.pytest-layout-enforcer.layouts]]
source = "src/my_package"
tests = "src/my_package/tests"
```

Paths are relative to `pyproject.toml`. Add more layout tables for monorepos.
The tool ignores `__init__.py` by default and only examines files named
`test_*.py` in test roots. `conftest.py` and test helper modules are therefore
left alone.

`require-tests = false` checks that every discovered test maps to a source
module without requiring every source module to have tests. Set it to `true`
to require at least one matching test file per source module.

## Usage

The plugin runs automatically before pytest collection when configuration is
present:

```console
uv run pytest
```

Run the same check without running tests:

```console
uv run pytest-layout-enforcer check
uv run pytest-layout-enforcer check --format json
```

The command exits with status 0 on success, 1 for layout violations, and 2 for
configuration errors.

## Publishing

CI runs the test suite on Python 3.11 through 3.14 for every pull request and
push to `main`. Version tags such as `v0.1.0` build, smoke-test, attest, and
publish the wheel and source distribution to PyPI using Trusted Publishing.

Before the first release:

1. Create a GitHub environment named `pypi` in the repository settings.
2. In the PyPI project's Publishing settings, add a GitHub Trusted Publisher
   for this repository, workflow `release.yml`, and environment `pypi`.
3. Make sure the version in `pyproject.toml` matches the release tag.

Then publish a release with:

```console
git tag -a v0.1.0 -m "v0.1.0"
git push origin main --follow-tags
```

No PyPI API token or GitHub repository secret is required.

## Naming and ambiguity

A module such as `data_loader.py` permits `test_data_loader.py` and feature
files such as `test_data_loader_cache.py`. If a feature filename could refer
to multiple modules—for example when both `data.py` and `data_loader.py`
exist—the tool reports an `ambiguous-test` violation instead of guessing.

For projects that prefer unambiguous names, configure a double underscore:

```toml
[tool.pytest-layout-enforcer]
feature-separator = "__"
```

That produces names such as `test_data_loader__cache.py`.
