# `songml` -- text-first music composition tool

[![CI](https://github.com/YOUR_USERNAME/songml/workflows/CI/badge.svg)](https://github.com/YOUR_USERNAME/songml/actions)
[![codecov](https://codecov.io/gh/YOUR_USERNAME/songml/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/songml)

See [docs/songml_design_manifesto.md]

## Development Setup

After cloning the repository:

```bash
cd songml-utils
pip install -e ".[dev]"
pre-commit install
```

Run tests:
```bash
cd songml-utils
pytest
```

The pre-commit hooks will automatically format and lint your code before each commit. CI will run the same checks on push.
