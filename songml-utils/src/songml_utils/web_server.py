"""Web server for viewing SongML and ABC files with abcjs player."""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote

from .abc_exporter import to_abc_string
from .parser import ParseError, parse_songml


class ViewerHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for ABC viewer service."""

    def log_message(self, format, *args):
        """Override to customize logging format."""
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def do_GET(self):
        """Handle GET requests."""
        path = unquote(self.path)

        if path == "/":
            self._serve_viewer()
        elif path == "/api/files":
            self._serve_file_list()
        elif path.startswith("/api/abc/"):
            file_path = path[9:]  # Remove "/api/abc/" prefix
            self._serve_abc(file_path)
        else:
            self._send_error(404, "Not Found")

    def _serve_viewer(self):
        """Serve the HTML viewer page."""
        try:
            viewer_path = os.path.join(os.path.dirname(__file__), "data", "viewer.html")
            with open(viewer_path, encoding="utf-8") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        except FileNotFoundError:
            self._send_error(500, "Viewer HTML not found")

    def _serve_file_list(self):
        """Serve list of .songml and .abc files in CWD and subdirectories."""
        try:
            base_path = Path.cwd()
            files = []

            # Find all .songml and .abc files recursively
            for pattern in ("*.songml", "*.abc"):
                for file_path in base_path.rglob(pattern):
                    if file_path.is_file():
                        try:
                            relative_path = file_path.relative_to(base_path)
                            file_type = "songml" if file_path.suffix == ".songml" else "abc"
                            files.append(
                                {
                                    "path": str(relative_path).replace("\\", "/"),
                                    "type": file_type,
                                    "name": file_path.name,
                                }
                            )
                        except (ValueError, OSError) as e:
                            # Skip files we can't process
                            sys.stderr.write(f"Warning: Skipping {file_path}: {e}\n")

            # Sort by path
            files.sort(key=lambda f: f["path"])

            response = json.dumps(files, indent=2)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(response.encode("utf-8"))

        except Exception as e:
            self._send_error(500, f"Error listing files: {e}")

    def _serve_abc(self, file_path):
        """Serve ABC content, converting from .songml if needed."""
        try:
            # Prevent directory traversal attacks
            base_path = Path.cwd().resolve()
            requested_path = (base_path / file_path).resolve()

            # Ensure the resolved path is under base_path
            try:
                requested_path.relative_to(base_path)
            except ValueError:
                self._send_error(403, "Access denied: path outside working directory")
                return

            if not requested_path.exists():
                self._send_error(404, f"File not found: {file_path}")
                return

            if not requested_path.is_file():
                self._send_error(400, f"Not a file: {file_path}")
                return

            # Read file content
            with open(requested_path, encoding="utf-8") as f:
                content = f.read()

            # Convert .songml to ABC, or serve .abc directly
            if requested_path.suffix == ".songml":
                try:
                    doc = parse_songml(content)

                    # Include warnings in output if any
                    warnings_text = ""
                    if doc.warnings:
                        warnings_text = "% Warnings:\n"
                        for warning in doc.warnings:
                            warnings_text += f"% - {warning}\n"
                        warnings_text += "\n"

                    abc_content = to_abc_string(doc)
                    content = warnings_text + abc_content

                except ParseError as e:
                    self._send_error(400, f"Parse error in {file_path}:\n\n{str(e)}")
                    return
                except ValueError as e:
                    self._send_error(400, f"Conversion error in {file_path}:\n\n{str(e)}")
                    return

            elif requested_path.suffix != ".abc":
                self._send_error(400, f"Unsupported file type: {requested_path.suffix}")
                return

            # Send ABC content
            self.send_response(200)
            self.send_header("Content-Type", "text/vnd.abc; charset=utf-8")
            self.send_header("Content-Length", str(len(content.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

        except Exception as e:
            self._send_error(500, f"Error serving file: {e}")

    def _send_error(self, code, message):
        """Send an error response with plain text message."""
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(message.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))


def main():
    """Run the ABC viewer web server."""
    parser = argparse.ArgumentParser(
        description="Start a local web server for viewing SongML and ABC files"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to run the server on (default: 8000)"
    )

    args = parser.parse_args()

    server = None
    try:
        server = HTTPServer(("localhost", args.port), ViewerHTTPRequestHandler)
        print(f"SongML ABC Viewer running at http://localhost:{args.port}/")
        print("Press Ctrl+C to stop the server")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        return 0
    except OSError as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        return 1
    finally:
        if server:
            server.server_close()


if __name__ == "__main__":
    sys.exit(main())
