"""Tests for web_server module."""

import errno
import os
import signal
import socket
import time
from io import BytesIO
from unittest.mock import Mock, patch

from songml_utils.web_server import _force_free_port, _make_handler, _pids_listening_on_port, main

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


def _make_request_raw(handler_cls, method: str, path: str) -> tuple[int, bytes, list]:
    """Invoke a handler method and return (status_code, body_bytes, send_header_calls)."""
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
    body = handler.wfile.getvalue()
    headers = [call.args for call in handler.send_header.call_args_list]
    return status, body, headers


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


class TestMidiEndpoint:
    def test_generates_midi_for_valid_songml(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8)

        status, body, headers = _make_request_raw(handler_cls, "GET", "/midi/test.songml")

        assert status == 200
        assert body[:4] == b"MThd"  # MIDI magic bytes
        assert ("Content-Type", "audio/midi") in headers
        assert any(h[0] == "Content-Disposition" and "test.mid" in h[1] for h in headers)

    def test_returns_404_for_missing_file(self, tmp_path):
        handler_cls = _make_handler(tmp_path, bars_per_row=8)
        status, _, _ = _make_request_raw(handler_cls, "GET", "/midi/nonexistent.songml")
        assert status == 404

    def test_returns_403_for_path_traversal(self, tmp_path):
        handler_cls = _make_handler(tmp_path, bars_per_row=8)
        status, _, _ = _make_request_raw(handler_cls, "GET", "/midi/../../etc/passwd")
        assert status in (403, 404)

    def test_song_page_contains_midi_button(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8)

        status, body = _make_request(handler_cls, "GET", "/song/test.songml")

        assert status == 200
        assert "/midi/test.songml" in body
        assert "midi-btn" in body


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

    def test_main_bind_conflict_without_force_returns_error(self, tmp_path, capsys):
        with patch("songml_utils.web_server.ThreadingHTTPServer") as mock_cls:
            mock_cls.side_effect = OSError(errno.EADDRINUSE, "Address already in use")

            with patch("sys.argv", ["songml-serve", "--root", str(tmp_path), "--port", "9001"]):
                result = main()

        assert result == 1
        assert "--force-port-grab" in capsys.readouterr().err

    def test_main_force_port_grab_retries_after_freeing(self, tmp_path):
        mock_srv = Mock()
        mock_srv.serve_forever.side_effect = KeyboardInterrupt()

        with (
            patch("songml_utils.web_server.ThreadingHTTPServer") as mock_cls,
            patch("songml_utils.web_server._force_free_port", return_value=True) as mock_free,
        ):
            mock_cls.side_effect = [OSError(errno.EADDRINUSE, "in use"), mock_srv]

            with patch(
                "sys.argv",
                ["songml-serve", "--root", str(tmp_path), "--port", "9002", "--force-port-grab"],
            ):
                result = main()

        assert result == 0
        mock_free.assert_called_once_with(9002)

    def test_main_force_port_grab_fails_to_free(self, tmp_path, capsys):
        with (
            patch("songml_utils.web_server.ThreadingHTTPServer") as mock_cls,
            patch("songml_utils.web_server._force_free_port", return_value=False),
        ):
            mock_cls.side_effect = OSError(errno.EADDRINUSE, "in use")

            with patch(
                "sys.argv",
                ["songml-serve", "--root", str(tmp_path), "--port", "9003", "--force-port-grab"],
            ):
                result = main()

        assert result == 1
        assert "could not free port" in capsys.readouterr().err

    def test_main_bind_error_unrelated_to_address_in_use_reraises(self, tmp_path):
        with patch("songml_utils.web_server.ThreadingHTTPServer") as mock_cls:
            mock_cls.side_effect = OSError(errno.EACCES, "Permission denied")

            with patch("sys.argv", ["songml-serve", "--root", str(tmp_path), "--port", "9004"]):
                try:
                    main()
                    raised = False
                except OSError:
                    raised = True

        assert raised


class TestPidsListeningOnPort:
    def test_finds_own_pid_on_bound_listening_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
        try:
            pids = _pids_listening_on_port(port)
        finally:
            s.close()

        assert os.getpid() in pids

    def test_empty_for_port_with_no_listener(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()

        assert _pids_listening_on_port(port) == set()


class TestForceFreePort:
    def test_no_pids_returns_true_immediately(self, monkeypatch):
        monkeypatch.setattr("songml_utils.web_server._pids_listening_on_port", lambda port: set())

        assert _force_free_port(9010) is True

    def test_sigterm_frees_port(self, monkeypatch):
        remaining = {12345}
        calls = []

        def fake_pids(port):
            return set(remaining)

        def fake_kill(pid, sig):
            calls.append((pid, sig))
            if sig == signal.SIGTERM:
                remaining.discard(pid)

        monkeypatch.setattr("songml_utils.web_server._pids_listening_on_port", fake_pids)
        monkeypatch.setattr(os, "getpid", lambda: 1)
        monkeypatch.setattr(os, "kill", fake_kill)

        assert _force_free_port(9011, timeout=1) is True
        assert (12345, signal.SIGTERM) in calls
        assert all(sig != signal.SIGKILL for _, sig in calls)

    def test_escalates_to_sigkill_when_sigterm_ignored(self, monkeypatch):
        calls = []

        monkeypatch.setattr("songml_utils.web_server._pids_listening_on_port", lambda port: {12345})
        monkeypatch.setattr(os, "getpid", lambda: 1)
        monkeypatch.setattr(os, "kill", lambda pid, sig: calls.append((pid, sig)))
        monkeypatch.setattr(time, "sleep", lambda s: None)

        result = _force_free_port(9012, timeout=0.05)

        assert result is False
        assert (12345, signal.SIGKILL) in calls

    def test_never_kills_own_pid(self, monkeypatch):
        calls = []

        monkeypatch.setattr(
            "songml_utils.web_server._pids_listening_on_port", lambda port: {os.getpid()}
        )
        monkeypatch.setattr(os, "kill", lambda pid, sig: calls.append((pid, sig)))

        assert _force_free_port(9013) is True
        assert calls == []

import json


def _make_post_request(handler_cls, payload: dict) -> tuple[int, dict]:
    """POST a JSON payload to /api/save; return (status_code, parsed JSON body)."""
    raw = json.dumps(payload).encode("utf-8")
    handler = object.__new__(handler_cls)
    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()
    handler.wfile = BytesIO()
    handler.rfile = BytesIO(raw)
    handler.headers = {"Content-Length": str(len(raw))}
    handler.path = "/api/save"
    handler.command = "POST"
    handler.log_date_time_string = Mock(return_value="00:00:00")

    handler.do_POST()

    status = handler.send_response.call_args[0][0]
    body = json.loads(handler.wfile.getvalue().decode("utf-8"))
    return status, body


_WARN_SONGML = """\
Title: Warn Song
Key: Cmaj
Tempo: 120
Time: 4/4

[Intro - 2 bars]
|  0  |  1  |
| C   | G   |

[Intro - 2 bars]
|  2  |  3  |
| Am  | F   |
"""


class TestApiSource:
    def test_disabled_without_server_token(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8)
        status, _ = _make_request(handler_cls, "GET", "/api/source?path=test.songml&token=x")
        assert status == 503

    def test_rejects_missing_token(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8, write_token="secret")
        status, _ = _make_request(handler_cls, "GET", "/api/source?path=test.songml")
        assert status == 403

    def test_rejects_wrong_token(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8, write_token="secret")
        status, _ = _make_request(handler_cls, "GET", "/api/source?path=test.songml&token=wrong")
        assert status == 403

    def test_returns_content(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8, write_token="secret")
        status, body = _make_request(
            handler_cls, "GET", "/api/source?path=test.songml&token=secret"
        )
        assert status == 200
        data = json.loads(body)
        assert data["ok"] is True
        assert data["content"] == _MINIMAL_SONGML

    def test_rejects_path_traversal(self, tmp_path):
        handler_cls = _make_handler(tmp_path, bars_per_row=8, write_token="secret")
        status, _ = _make_request(
            handler_cls, "GET", "/api/source?path=../evil.songml&token=secret"
        )
        assert status == 403

    def test_404_for_missing_song(self, tmp_path):
        handler_cls = _make_handler(tmp_path, bars_per_row=8, write_token="secret")
        status, _ = _make_request(
            handler_cls, "GET", "/api/source?path=nope.songml&token=secret"
        )
        assert status == 404

    def test_rejects_non_songml(self, tmp_path):
        (tmp_path / "notes.txt").write_text("hi", encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8, write_token="secret")
        status, _ = _make_request(
            handler_cls, "GET", "/api/source?path=notes.txt&token=secret"
        )
        assert status == 404


class TestApiSave:
    def test_disabled_without_server_token(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8)
        status, _ = _make_post_request(
            handler_cls, {"path": "test.songml", "content": _MINIMAL_SONGML, "token": "x"}
        )
        assert status == 503

    def test_rejects_wrong_token(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8, write_token="secret")
        status, data = _make_post_request(
            handler_cls, {"path": "test.songml", "content": _MINIMAL_SONGML, "token": "wrong"}
        )
        assert status == 403
        assert data["ok"] is False
        assert (tmp_path / "test.songml").read_text(encoding="utf-8") == _MINIMAL_SONGML

    def test_saves_valid_content(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8, write_token="secret")
        new_content = _MINIMAL_SONGML.replace("Test Song", "Edited Song")
        status, data = _make_post_request(
            handler_cls, {"path": "test.songml", "content": new_content, "token": "secret"}
        )
        assert status == 200
        assert data["ok"] is True
        assert isinstance(data["warnings"], list)
        assert (tmp_path / "test.songml").read_text(encoding="utf-8") == new_content

    def test_rejects_unparseable_content(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8, write_token="secret")
        status, data = _make_post_request(
            handler_cls, {"path": "test.songml", "content": "[Verse]\n| C | G |\n", "token": "secret"}
        )
        assert status == 422
        assert data["ok"] is False
        assert "error" in data
        # file untouched
        assert (tmp_path / "test.songml").read_text(encoding="utf-8") == _MINIMAL_SONGML

    def test_warnings_do_not_block_save(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8, write_token="secret")
        status, data = _make_post_request(
            handler_cls, {"path": "test.songml", "content": _WARN_SONGML, "token": "secret"}
        )
        assert status == 200
        assert data["ok"] is True
        assert len(data["warnings"]) > 0
        assert (tmp_path / "test.songml").read_text(encoding="utf-8") == _WARN_SONGML

    def test_rejects_path_traversal(self, tmp_path):
        handler_cls = _make_handler(tmp_path, bars_per_row=8, write_token="secret")
        status, _ = _make_post_request(
            handler_cls, {"path": "../evil.songml", "content": _MINIMAL_SONGML, "token": "secret"}
        )
        assert status == 403
        assert not (tmp_path.parent / "evil.songml").exists()

    def test_rejects_non_songml(self, tmp_path):
        handler_cls = _make_handler(tmp_path, bars_per_row=8, write_token="secret")
        status, _ = _make_post_request(
            handler_cls, {"path": "notes.txt", "content": "hi", "token": "secret"}
        )
        assert status == 404

    def test_rejects_missing_content(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8, write_token="secret")
        status, data = _make_post_request(handler_cls, {"path": "test.songml", "token": "secret"})
        assert status == 400
        assert data["ok"] is False


class TestEditButton:
    def test_song_page_has_edit_button_when_token_set(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8, write_token="secret")
        status, body = _make_request(handler_cls, "GET", "/song/test.songml")
        assert status == 200
        assert 'id="songml-edit-btn"' in body
        assert '"secret"' in body  # token embedded in the page JS

    def test_song_page_has_no_edit_button_without_token(self, tmp_path):
        (tmp_path / "test.songml").write_text(_MINIMAL_SONGML, encoding="utf-8")
        handler_cls = _make_handler(tmp_path, bars_per_row=8)
        status, body = _make_request(handler_cls, "GET", "/song/test.songml")
        assert status == 200
        assert "songml-edit-btn" not in body
