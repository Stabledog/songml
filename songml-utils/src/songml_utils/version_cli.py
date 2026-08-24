"""Print the installed songml-utils version."""

from __future__ import annotations

import argparse

from . import __version__


def main() -> None:
    """CLI entry point for songml-version command."""
    parser = argparse.ArgumentParser(
        description="Print the songml-utils version (x.y.z) of the installed package."
    )
    parser.parse_args()

    print(__version__)


if __name__ == "__main__":  # pragma: no cover
    main()
