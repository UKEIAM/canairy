# Development

Dependencies are managed with [uv](https://docs.astral.sh/uv/); `uv.lock` is committed.

```sh
uv sync                            # install with dev dependencies
uv run pytest                      # all tests, including live API calls
uv run ruff check src tests
uv run mypy src

# offline tests only
uv run pytest --ignore=tests/hh/test_hh_client.py --ignore=tests/be/test_be_client.py --ignore=tests/ni/test_ni_client.py --ignore=tests/nrw/test_nrw_client.py --ignore-glob='tests/uba/test_get_*.py'

# tests with coverage
uv run coverage run -m pytest && uv run coverage report
```

Supported Python versions are 3.12–3.15; mypy checks against 3.12. Test another version with
`uv run --python 3.15 --isolated pytest …`.

## Tests

- The `test_*_client.py` files of each network and `tests/uba/test_get_*.py` are integration
  tests against the real APIs: they need network access and are subject to rate limits and
  caching.
- All other tests are offline. They build clients on `httpx2.MockTransport`, wrapped in the
  retry and rate-limit layers.

## Documentation

The documentation is built with [MkDocs](https://www.mkdocs.org) and
[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/); its dependencies are in
the `docs` group.

```sh
uv run --group docs mkdocs serve           # preview at http://127.0.0.1:8000
uv run --group docs mkdocs build --strict  # build into site/
```

## CI

`.github/workflows/tests.yml` runs on pushes to `develop`, pull requests and manually:

- ruff, mypy and a strict documentation build
- offline tests on Python 3.12–3.15
- live integration tests once on Python 3.15 (not per version, to respect the APIs' rate limits)
- combined coverage report; on pushes to `develop` it updates the README coverage badge
