"""Tests for bash completion script generation."""

from __future__ import annotations

from unittest.mock import Mock, mock_open

import pytest

from songml_utils.bashcompletion import load_completion_script, main


class TestBashCompletion:
    """Tests for bash completion functionality."""

    def test_load_completion_script_returns_string_with_comp_words(self, monkeypatch):
        """load_completion_script returns non-empty string containing COMP_WORDS."""
        script_content = "#!/bin/bash\n# Completion script\nCOMP_WORDS=()\n"

        # Mock open to return our test script
        monkeypatch.setattr("builtins.open", mock_open(read_data=script_content))

        result = load_completion_script()

        assert isinstance(result, str)
        assert len(result) > 0
        assert "COMP_WORDS" in result
        assert result == script_content

    def test_load_completion_script_minimal_semantic_check(self, monkeypatch):
        """load_completion_script result contains expected bash keywords."""
        script_content = (
            "#!/bin/bash\nCOMP_WORDS=()\ncomplete -o default -F _songml songml-to-midi\n"
        )

        monkeypatch.setattr("builtins.open", mock_open(read_data=script_content))

        result = load_completion_script()

        # Basic semantic checks: bash keywords
        assert "COMP_WORDS" in result
        assert "#!/bin/bash" in result
        assert "complete" in result

    def test_load_completion_script_file_not_found(self, monkeypatch):
        """load_completion_script raises FileNotFoundError when file missing."""
        monkeypatch.setattr("builtins.open", Mock(side_effect=FileNotFoundError("Not found")))

        with pytest.raises(FileNotFoundError):
            load_completion_script()

    def test_main_forwards_script_to_stdout(self, monkeypatch, capsys):
        """main() calls load_completion_script and prints result to stdout."""
        script_content = "#!/bin/bash\nCOMP_WORDS=()\ncomplete -F _songml songml-format\n"

        mock_load = Mock(return_value=script_content)
        monkeypatch.setattr("songml_utils.bashcompletion.load_completion_script", mock_load)
        monkeypatch.setattr("sys.argv", ["songml-bashcompletion"])

        main()

        # Verify script was loaded
        mock_load.assert_called_once()

        # Verify script forwarded to stdout
        captured = capsys.readouterr()
        assert script_content in captured.out

    def test_main_script_contains_comp_words(self, monkeypatch, capsys):
        """main() output contains COMP_WORDS keyword."""
        script_content = (
            "#!/bin/bash\nCOMP_WORDS=(${words[@]})\ncomplete -F _songml songml-create\n"
        )

        mock_load = Mock(return_value=script_content)
        monkeypatch.setattr("songml_utils.bashcompletion.load_completion_script", mock_load)
        monkeypatch.setattr("sys.argv", ["songml-bashcompletion"])

        main()

        captured = capsys.readouterr()
        assert "COMP_WORDS" in captured.out
