"""LAN web server for viewing SongML files as beat-grid chord charts."""

from __future__ import annotations

import argparse
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from .html_exporter import _CSS, to_html_string
from .parser import ParseError, parse_songml

_INDEX_CSS = (
    _CSS
    + """
body{padding:2rem}
h1{margin-bottom:1rem}
ul{list-style:none;padding:0;margin:0}
li{margin:.4rem 0;font-size:1rem}
"""
)


class _Handler(BaseHTTPRequestHandler):
    root: Path
    bars_per_row: int

    def log_message(self, format, *args):  # noqa: A002
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def do_GET(self):
        path = unquote(self.path).split("?")[0]
        if path == "/":
            self._serve_index()
        elif path.startswith("/song/"):
            self._serve_song(path[len("/song/") :])
        else:
            self._send(404, "text/plain", b"Not found")

    def do_HEAD(self):
        self.do_GET()

    def _serve_index(self):
        files = sorted(self.__class__.root.rglob("*.songml"))
        items = "".join(
            f'<li><a href="/song/{f.relative_to(self.__class__.root)}">'
            f"{f.relative_to(self.__class__.root)}</a></li>"
            for f in files
        )
        body = (
            f'<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
            f"<title>SongML Library</title>"
            f"<style>{_INDEX_CSS}</style></head>"
            f"<body><div class='song'><h1>SongML Library</h1>"
            f"<ul>{items}</ul></div></body></html>"
        )
        self._send(200, "text/html; charset=utf-8", body.encode())

    def _serve_song(self, rel_path: str):
        base = self.__class__.root.resolve()
        target = (base / rel_path).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            self._send(403, "text/plain", b"Access denied")
            return
        if not target.exists() or not target.is_file():
            self._send(404, "text/plain", f"Not found: {rel_path}".encode())
            return
        try:
            doc = parse_songml(target.read_text(encoding="utf-8"))
            rendered = to_html_string(doc, bars_per_row=self.__class__.bars_per_row)
            self._send(200, "text/html; charset=utf-8", rendered.encode())
        except ParseError as e:
            self._send(400, "text/plain", str(e).encode())
        except Exception as e:
            self._send(500, "text/plain", str(e).encode())

    def _send(self, code: int, content_type: str, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)


def _make_handler(root: Path, bars_per_row: int) -> type[_Handler]:
    class Handler(_Handler):
        pass

    Handler.root = root
    Handler.bars_per_row = bars_per_row
    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Serve SongML files as chord charts over HTTP (LAN)"
    )
    parser.add_argument("--root", default=".", help="Directory of .songml files (default: .)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--bars-per-row", type=int, default=8, metavar="N",
                        help="Bars per display row (default: 8)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        return 1

    handler = _make_handler(root, args.bars_per_row)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    print(f"SongML server:  http://localhost:{args.port}/")
    print(f"Serving files:  {root}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
