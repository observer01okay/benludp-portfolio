#!/usr/bin/env python3
"""Static file server with HTTP Range support (needed for HTML5 video seeking)."""

from __future__ import annotations

import argparse
import mimetypes
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


class RangeRequestHandler(BaseHTTPRequestHandler):
    # Set by main()
    root: Path = Path(".").resolve()

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_HEAD(self) -> None:
        self._serve(head_only=True)

    def do_GET(self) -> None:
        self._serve(head_only=False)

    def _resolve(self) -> Path | None:
        parsed = urlparse(self.path)
        rel = unquote(parsed.path)
        if rel.endswith("/"):
            rel += "index.html"
        rel = rel.lstrip("/")
        candidate = (self.root / rel).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError:
            return None
        if candidate.is_file():
            return candidate
        # /reel → /reel/index.html
        as_index = (self.root / rel / "index.html").resolve()
        try:
            as_index.relative_to(self.root)
        except ValueError:
            return None
        if as_index.is_file():
            return as_index
        return None

    def _serve(self, head_only: bool) -> None:
        path = self._resolve()
        if path is None:
            self.send_error(404, "File not found")
            return

        file_size = path.stat().st_size
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        range_header = self.headers.get("Range")

        start, end = 0, file_size - 1
        status = 200
        if range_header:
            m = RANGE_RE.fullmatch(range_header.strip())
            if not m:
                self.send_error(416, "Invalid Range")
                return
            start_s, end_s = m.groups()
            if start_s == "" and end_s == "":
                self.send_error(416, "Invalid Range")
                return
            if start_s == "":
                # suffix bytes: last N bytes
                suffix = int(end_s)
                start = max(file_size - suffix, 0)
                end = file_size - 1
            else:
                start = int(start_s)
                end = int(end_s) if end_s else file_size - 1
            if start >= file_size or end >= file_size or start > end:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{file_size}")
                self.end_headers()
                return
            status = 206

        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.send_header("Last-Modified", self.date_time_string(path.stat().st_mtime))
        self.send_header("Cache-Control", "public, max-age=0")
        self.end_headers()

        if head_only:
            return

        with path.open("rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except BrokenPipeError:
                    return
                remaining -= len(chunk)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "dist",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        sys.exit(f"Root not found: {root}")

    RangeRequestHandler.root = root
    server = ThreadingHTTPServer(("127.0.0.1", args.port), RangeRequestHandler)
    print(f"Serving {root} at http://127.0.0.1:{args.port} (Range requests enabled)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
