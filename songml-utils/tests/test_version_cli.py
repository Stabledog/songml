"""Tests for the songml-version CLI command."""

from __future__ import annotations

import re

from songml_utils import __version__
from songml_utils.version_cli import main


class TestVersionCli:
    """Tests for the songml-version command."""

    def test_main_prints_package_version(self, monkeypatch, capsys):
        """main() prints exactly the package's __version__."""
        monkeypatch.setattr("sys.argv", ["songml-version"])

        main()

        captured = capsys.readouterr()
        assert captured.out == f"{__version__}\n"

    def test_version_is_semver(self):
        """__version__ is an unambiguous x.y.z string."""
        assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)
