# Releasing

## One-time setup on PyPI

Nonio publishes through **Trusted Publishing**, so there is no API token stored
in repository secrets. Register the publisher once:

1. Go to <https://pypi.org/manage/account/publishing/>
2. Add a new **pending publisher**:
   - PyPI project name: `nonio`
   - Owner: `JoaquinRuiz`
   - Repository: `nonio`
   - Workflow: `publish.yml`
   - Environment: `pypi`
3. In GitHub → Settings → Environments, create an environment called `pypi`.
   Adding a required reviewer there means a release cannot go out without a
   human approving it.

The name `nonio` was available on PyPI when this was written; the pending
publisher reserves it on first publish.

## Before each release

```bash
python -m nonio.evaluation.bundle     # refresh the distributed corpus
pytest tests/                          # everything, including model-dependent
ruff check . && black --check .
python -m build && twine check dist/*
```

Then install the wheel into a clean environment and check the command actually
runs — a packaging bug is invisible to every logic test:

```bash
uv venv /tmp/v && uv pip install --python /tmp/v/bin/python dist/*.whl
/tmp/v/bin/nonio schema --version
/tmp/v/bin/nonio profiles
```

## Versioning

Two independent version numbers, and they must not be conflated (Article VI):

- **Package version** in `pyproject.toml` — ordinary semver for the software.
- **`schema_version`** in `nonio/schema/models.py` — versions the output
  contract. Adding a field is MINOR; removing one or changing what an existing
  one means is MAJOR.

They may coincide by accident. Neither is derived from the other, and a test
enforces that.

## What must be true before 1.0

Nonio is `0.1.0` and should stay below 1.0 until the calibration is publishable.
Right now the FR-030 bias gate returns **inconclusive**, so no default threshold
ships and `analyze()` abstains unless a table is passed explicitly.

A 1.0 needs, at minimum:

- The bias gate returning `pasa` — the whole confidence interval below 2.0×, not
  just the point estimate
- The `mixto` corpus category populated, which needs human contributors
- A default calibration table shipped with the package

Publishing a 1.0 that implies "ready to use" while the instrument cannot state
its own error rate would contradict Article III in the version number itself.

## Cutting a release

```bash
git tag -a v0.1.0 -m "..." && git push origin v0.1.0
```

Then create a GitHub Release from the tag. `publish.yml` runs on
`release: published`, re-runs the suite, builds, and publishes.
