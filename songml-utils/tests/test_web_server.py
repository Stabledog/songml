"""Tests for web_server module."""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

from songml_utils.web_server import _make_handler, main

_MINIMAL_SONGML = """\
Title: Test Song
Key: Cmaj
Tempo: 120
Time: 4/4

[Intro - 2 bars]
|  0  |  1  |
| C   | G   |
"""


def _make_request(handler_cls, method: str, path: str) -> tuple[int, str]:
    """Invoke a handler method and return (status_code, body_text)."""
    handler = object.__new__(handler_cls)
    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()
    handler.wfile = BytesIO()
    handler.path = path
    handler.command = method
    handler.log_date_time_string = Mock(return_value="00:00:00")

    getattr(handler, f"do_{method}")()

    status = handler.send_response.call_args[0][0]
    body = handler.wfile.getvalue().decode("utf-8")
    return status, body


class TestIndexPage:
    def test_lists_songml_files(self, tmp_path):
        (tmp_path / "alpha.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        (tmp_path / "beta.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8)

        status, body = _make_request(handler_cls, "GET", "/")

        assert status == 200
        assert "alpha.songml" in body
        assert "beta.songml" in body

    def test_empty_directory(self, tmp_path):
        handler_cls = _make_handler(tmp_path, bars_per_row=8)
        status, body = _make_request(handler_cls, "GET", "/")
        assert status == 200
        assert "<ul>" in body

    def test_finds_files_in_subdirectory(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "nested.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8)

        status, body = _make_request(handler_cls, "GET", "/")

        assert status == 200
        assert "nested.songml" in body


class TestSongPage:
    def test_renders_valid_songml(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8)

        status, body = _make_request(handler_cls, "GET", "/song/test.songml")

        assert status == 200
        assert "Test Song" in body
        assert "strip" in body
        assert "chord" in body

    def test_returns_404_for_missing_file(self, tmp_path):
        handler_cls = _make_handler(tmp_path, bars_per_row=8)
        status, _ = _make_request(handler_cls, "GET", "/song/nonexistent.songml")
        assert status == 404

    def test_returns_403_for_path_traversal(self, tmp_path):
        handler_cls = _make_handler(tmp_path, bars_per_row=8)
        status, _ = _make_request(handler_cls, "GET", "/song/../../etc/passwd")
        assert status in (403, 404)

    def test_song_html_contains_key_and_tempo(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8)

        status, body = _make_request(handler_cls, "GET", "/song/test.songml")

        assert status == 200
        assert "Cmaj" in body
        assert "120" in body


class TestUnknownRoute:
    def test_returns_404(self, tmp_path):
        handler_cls = _make_handler(tmp_path, bars_per_row=8)
        status, _ = _make_request(handler_cls, "GET", "/unknown/path")
        assert status == 404


class TestCLI:
    def test_main_prints_url(self, tmp_path, capsys):
        with patch("songml_utils.web_server.ThreadingHTTPServer") as mock_cls:
            mock_srv = Mock()
            mock_cls.return_value = mock_srv
            mock_srv.serve_forever.side_effect = KeyboardInterrupt()

            with patch("sys.argv", ["songml-serve", "--root", str(tmp_path)]):
                result = main()

        assert result == 0
        assert "http://localhost:8000" in capsys.readouterr().out

    def test_main_custom_port(self, tmp_path, capsys):
        with patch("songml_utils.web_server.ThreadingHTTPServer") as mock_cls:
            mock_srv = Mock()
            mock_cls.return_value = mock_srv
            mock_srv.serve_forever.side_effect = KeyboardInterrupt()

            with patch("sys.argv", ["songml-serve", "--root", str(tmp_path), "--port", "9000"]):
                result = main()

        assert result == 0
        assert "9000" in capsys.readouterr().out

    def test_main_invalid_root(self, capsys):
        with patch("sys.argv", ["songml-serve", "--root", "/nonexistent/path"]):
            result = main()
        assert result == 1
