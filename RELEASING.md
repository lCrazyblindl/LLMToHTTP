# Releasing `lap`

The toolkit and artifacts are prepared in-repo; **publishing needs the owner** (PyPI +
GitHub credentials the agent doesn't have). Steps:

## 1. Pre-flight
```bash
pip install -e ".[dev]"
pytest -q                      # full suite green
python -m lap.lint lap/examples/bookstore.openapi.json   # smoke
```
Confirm `version` in `pyproject.toml` and the top section of `CHANGELOG.md` match the
release you intend to cut (currently **0.3.0**).

## 2. Build the distribution
```bash
python -m pip install --upgrade build twine
python -m build                # -> dist/lap_score-<version>.tar.gz + .whl
twine check dist/*
```

## 3. Publish to PyPI (owner)
```bash
# optional dry run on TestPyPI first:
# twine upload -r testpypi dist/*
twine upload dist/*            # needs a PyPI API token (e.g. TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-...)
```
After this, `pip install lap-score` works for everyone (and the GitHub Action installs
from PyPI instead of falling back to git).

## 4. Cut the GitHub release (owner)
```bash
git tag v0.3.0
git push origin v0.3.0
gh release create v0.3.0 dist/* --title "lap 0.3.0" \
  --notes-file <(awk '/^## \[0.3.0\]/{f=1;next} /^## \[/{f=0} f' CHANGELOG.md)
```
Tagging `v0.3.0` also makes the composite Action usable as
`uses: lCrazyblindl/lap@v0.3.0`. To list it on the GitHub Marketplace, open the release
(or `action.yml`) on GitHub and choose **“Publish this Action to the Marketplace”** — it
requires accepting the developer agreement and a repo with a single top-level `action.yml`
(already present).

## Versioning
Pre-1.0, loose semver: bump the minor for new capabilities, patch for fixes. Update
`pyproject.toml` **and** add a dated `CHANGELOG.md` section in the same commit.
