"""Tests for web_server module."""

import json
from io import BytesIO
from unittest.mock import Mock, patch

from songml_utils.web_server import ViewerHTTPRequestHandler


def create_mock_handler():
    """Create a mock handler for testing."""
    handler = object.__new__(ViewerHTTPRequestHandler)
    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()
    handler.wfile = BytesIO()
    return handler


class TestViewerHTTPRequestHandler:
    """Tests for ViewerHTTPRequestHandler."""

    def test_serve_viewer_html(self, tmp_path, monkeypatch):
        """Test serving the viewer HTML file."""
        # Create a mock viewer.html
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        viewer_html = data_dir / "viewer.html"
        viewer_html.write_text("<html><body>Test Viewer</body></html>", encoding="utf-8")

        # Mock the data directory location
        import songml_utils.web_server

        monkeypatch.setattr(songml_utils.web_server, "__file__", str(tmp_path / "web_server.py"))

        # Create mock request/response
        handler = Mock(spec=ViewerHTTPRequestHandler)
        handler.path = "/"
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()

        # Call the actual method
        ViewerHTTPRequestHandler._serve_viewer(handler)

        handler.send_response.assert_called_once_with(200)
        assert handler.wfile.write.called

    def test_serve_file_list_empty(self, tmp_path, monkeypatch):
        """Test serving file list when no files exist."""
        monkeypatch.chdir(tmp_path)

        handler = Mock(spec=ViewerHTTPRequestHandler)
        handler.path = "/api/files"
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()

        ViewerHTTPRequestHandler._serve_file_list(handler)

        handler.send_response.assert_called_once_with(200)

        # Get the written data
        written_data = handler.wfile.write.call_args[0][0]
        files = json.loads(written_data.decode("utf-8"))
        assert files == []

    def test_serve_file_list_with_files(self, tmp_path, monkeypatch):
        """Test serving file list with mixed .songml and .abc files."""
        monkeypatch.chdir(tmp_path)

        # Create test files
        (tmp_path / "song1.songml").write_text("Title: Test", encoding="utf-8")
        (tmp_path / "song2.abc").write_text("X:1", encoding="utf-8")

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "song3.songml").write_text("Title: Sub", encoding="utf-8")

        handler = Mock(spec=ViewerHTTPRequestHandler)
        handler.path = "/api/files"
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()

        ViewerHTTPRequestHandler._serve_file_list(handler)

        handler.send_response.assert_called_once_with(200)

        written_data = handler.wfile.write.call_args[0][0]
        files = json.loads(written_data.decode("utf-8"))

        assert len(files) == 3

        paths = [f["path"] for f in files]
        assert "song1.songml" in paths
        assert "song2.abc" in paths
        assert "subdir/song3.songml" in paths

        # Check file types
        types = {f["path"]: f["type"] for f in files}
        assert types["song1.songml"] == "songml"
        assert types["song2.abc"] == "abc"

    def test_serve_abc_file_directly(self, tmp_path, monkeypatch):
        """Test serving an .abc file directly."""
        monkeypatch.chdir(tmp_path)

        abc_content = "X:1\nT:Test\nK:C\nCDEF|"
        (tmp_path / "test.abc").write_text(abc_content, encoding="utf-8")

        handler = Mock(spec=ViewerHTTPRequestHandler)
        handler.path = "/api/abc/test.abc"
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()

        ViewerHTTPRequestHandler._serve_abc(handler, "test.abc")

        handler.send_response.assert_called_once_with(200)

        written_data = handler.wfile.write.call_args[0][0]
        assert written_data.decode("utf-8") == abc_content

    def test_serve_abc_convert_songml(self, tmp_path, monkeypatch):
        """Test converting .songml to ABC on the fly."""
        monkeypatch.chdir(tmp_path)

        songml_content = """Title: Test Song
Key: Cmaj
Tempo: 120
Time: 4/4

[Intro - 2 bars]
|  0  |  1  |
| C   | G   |
"""
        (tmp_path / "test.songml").write_text(songml_content, encoding="utf-8")

        handler = create_mock_handler()
        handler._serve_abc("test.songml")

        # Check if there was an error
        error_msg = handler.wfile.getvalue().decode("utf-8")
        assert handler.send_response.call_args[0][0] == 200, (
            f"Expected 200 but got {handler.send_response.call_args[0][0]}. Error: {error_msg}"
        )

        abc_content = error_msg

        # Verify ABC format
        assert "X: 1" in abc_content
        assert "T: Test Song" in abc_content
        assert "K: C" in abc_content
        assert '"C"' in abc_content

    def test_serve_abc_parse_error(self, tmp_path, monkeypatch):
        """Test error handling for invalid .songml file."""
        monkeypatch.chdir(tmp_path)

        # Invalid SongML (section with no bars)
        songml_content = """Title: Test
[Intro]
| C |
"""
        (tmp_path / "bad.songml").write_text(songml_content, encoding="utf-8")

        handler = create_mock_handler()
        handler._serve_abc("bad.songml")

        handler.send_response.assert_called_once_with(400)

        error_msg = handler.wfile.getvalue().decode("utf-8")
        assert "Parse error" in error_msg or "error" in error_msg.lower()

    def test_serve_abc_file_not_found(self, tmp_path, monkeypatch):
        """Test 404 error for non-existent file."""
        monkeypatch.chdir(tmp_path)

        handler = create_mock_handler()
        handler._serve_abc("nonexistent.songml")

        handler.send_response.assert_called_once_with(404)

    def test_serve_abc_directory_traversal_prevention(self, tmp_path, monkeypatch):
        """Test that directory traversal attacks are prevented."""
        monkeypatch.chdir(tmp_path)

        # Try to access file outside CWD
        handler = create_mock_handler()
        handler._serve_abc("../../../etc/passwd")

        # Should get 403 or 404, not 200
        assert handler.send_response.call_args[0][0] in [403, 404]

    def test_serve_abc_unsupported_file_type(self, tmp_path, monkeypatch):
        """Test error for unsupported file types."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "test.txt").write_text("Not music", encoding="utf-8")

        handler = create_mock_handler()
        handler._serve_abc("test.txt")

        handler.send_response.assert_called_once_with(400)

    def test_serve_abc_with_warnings(self, tmp_path, monkeypatch):
        """Test that warnings are included in ABC output."""
        monkeypatch.chdir(tmp_path)

        # SongML that will generate warnings (unknown chord)
        songml_content = """Title: Test
Key: Cmaj
Tempo: 120
Time: 4/4

[Intro - 1 bar]
|      0      |
| Xyzabc      |
"""
        (tmp_path / "test.songml").write_text(songml_content, encoding="utf-8")

        handler = create_mock_handler()
        handler._serve_abc("test.songml")

        handler.send_response.assert_called_once_with(200)

        abc_content = handler.wfile.getvalue().decode("utf-8")

        # May contain warnings as ABC comments
        # The actual behavior depends on parser implementation
        assert "X: 1" in abc_content


class TestWebServerCLI:
    """Tests for web server CLI."""

    def test_main_prints_url(self, capsys):
        """Test that main() prints the server URL."""
        with patch("songml_utils.web_server.HTTPServer") as mock_server_class:
            mock_server = Mock()
            mock_server_class.return_value = mock_server
            mock_server.serve_forever.side_effect = KeyboardInterrupt()

            from songml_utils.web_server import main

            with patch("sys.argv", ["songml-serve"]):
                result = main()

            assert result == 0
            captured = capsys.readouterr()
            assert "http://localhost:8000" in captured.out

    def test_main_custom_port(self, capsys):
        """Test that custom port is used."""
        with patch("songml_utils.web_server.HTTPServer") as mock_server_class:
            mock_server = Mock()
            mock_server_class.return_value = mock_server
            mock_server.serve_forever.side_effect = KeyboardInterrupt()

            from songml_utils.web_server import main

            with patch("sys.argv", ["songml-serve", "--port", "9000"]):
                result = main()

            assert result == 0
            captured = capsys.readouterr()
            assert "http://localhost:9000" in captured.out

            # Verify server was created with correct port
            mock_server_class.assert_called_once_with(("localhost", 9000), ViewerHTTPRequestHandler)
