"""LAN web server for viewing SongML files as beat-grid chord charts."""

from __future__ import annotations

import argparse
import contextlib
import errno
import os
import signal
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from .chord_voicings import DEFAULT_VOICINGS_PATH, find_local_voicings_path
from .html_exporter import _CSS, to_html_string
from .midi_exporter import export_midi
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
        elif path.startswith("/midi/"):
            self._serve_midi(path[len("/midi/") :])
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
            rendered = to_html_string(
                doc,
                bars_per_row=self.__class__.bars_per_row,
                back_url="/",
                midi_url=f"/midi/{rel_path}",
            )
            self._send(200, "text/html; charset=utf-8", rendered.encode())
        except ParseError as e:
            self._send(400, "text/plain", str(e).encode())
        except Exception as e:
            self._send(500, "text/plain", str(e).encode())

    def _serve_midi(self, rel_path: str):
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
            fd, tmp_path = tempfile.mkstemp(suffix=".mid")
            os.close(fd)
            try:
                # Resolve explicitly (rather than only-if-found) since this is a
                # persistent server handling many songs: an unqualified reload
                # would leave a previous request's local table loaded.
                voicings_path = find_local_voicings_path(target) or DEFAULT_VOICINGS_PATH
                export_midi(doc, tmp_path, voicings_path)
                midi_bytes = Path(tmp_path).read_bytes()
            finally:
                os.unlink(tmp_path)
            filename = target.stem + ".mid"
            self.send_response(200)
            self.send_header("Content-Type", "audio/midi")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(midi_bytes)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(midi_bytes)
        except (ParseError, ValueError) as e:
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


def _pids_listening_on_port(port: int) -> set[int]:
    """Find PIDs with a socket in LISTEN state bound to the given TCP port.

    Parses /proc directly (Linux-only) so this works with no external tools
    (lsof, fuser, ss) required.
    """
    target_hex = f"{port:04X}"
    inodes: set[str] = set()
    for proc_file in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(proc_file, encoding="ascii") as f:
                next(f)  # header row
                for line in f:
                    fields = line.split()
                    local_addr, state, inode = fields[1], fields[3], fields[9]
                    local_port = local_addr.rsplit(":", 1)[-1]
                    if local_port.upper() == target_hex and state == "0A":  # TCP_LISTEN
                        inodes.add(inode)
        except FileNotFoundError:
            continue

    if not inodes:
        return set()

    pids: set[int] = set()
    for pid_dir in Path("/proc").iterdir():
        if not pid_dir.name.isdigit():
            continue
        try:
            for fd in (pid_dir / "fd").iterdir():
                try:
                    target = os.readlink(fd)
                except OSError:
                    continue
                if target.startswith("socket:[") and target[8:-1] in inodes:
                    pids.add(int(pid_dir.name))
                    break
        except (FileNotFoundError, PermissionError):
            continue
    return pids


def _describe_pid(pid: int) -> str:
    try:
        comm = Path(f"/proc/{pid}/comm").read_text(encoding="utf-8").strip()
    except OSError:
        comm = "?"
    return f"pid {pid} ({comm})"


def _force_free_port(port: int, timeout: float = 3.0) -> bool:
    """Kill whatever is listening on `port`. Returns True once the port is free.

    Sends SIGTERM first, then SIGKILL to anything still holding the port
    after `timeout` seconds. Never targets our own process.
    """
    pids = _pids_listening_on_port(port) - {os.getpid()}
    if not pids:
        return True

    for pid in pids:
        print(
            f"--force-port-grab: killing {_describe_pid(pid)} to free port {port}",
            file=sys.stderr,
        )
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError:
            print(f"--force-port-grab: permission denied killing pid {pid}", file=sys.stderr)

    deadline = time.monotonic() + timeout
    remaining = pids
    while time.monotonic() < deadline:
        remaining = _pids_listening_on_port(port) - {os.getpid()}
        if not remaining:
            return True
        time.sleep(0.1)

    for pid in remaining:
        print(
            f"--force-port-grab: {_describe_pid(pid)} didn't exit, sending SIGKILL",
            file=sys.stderr,
        )
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, signal.SIGKILL)
    time.sleep(0.2)

    return not (_pids_listening_on_port(port) - {os.getpid()})


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Serve SongML files as chord charts over HTTP (LAN)"
    )
    parser.add_argument("--root", default=".", help="Directory of .songml files (default: .)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument(
        "--bars-per-row", type=int, default=8, metavar="N", help="Bars per display row (default: 8)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Auto-restart when source files change (development mode)",
    )
    parser.add_argument(
        "--force-port-grab",
        action="store_true",
        help="If --port is already in use, kill whatever is listening on it and take it over",
    )
    args = parser.parse_args()

    if args.reload:
        from hupper import start_reloader

        start_reloader("songml_utils.web_server.main")

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        return 1

    handler = _make_handler(root, args.bars_per_row)
    try:
        server = ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    except OSError as e:
        if e.errno != errno.EADDRINUSE:
            raise
        if not args.force_port_grab:
            print(
                f"Error: port {args.port} is already in use "
                f"(use --force-port-grab to take it over)",
                file=sys.stderr,
            )
            return 1
        if not _force_free_port(args.port):
            print(f"Error: could not free port {args.port}", file=sys.stderr)
            return 1
        try:
            server = ThreadingHTTPServer(("0.0.0.0", args.port), handler)
        except OSError as e2:
            print(
                f"Error: port {args.port} still in use after --force-port-grab: {e2}",
                file=sys.stderr,
            )
            return 1

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
