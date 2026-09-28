"""Preview the static project page with byte-range video seeking on loopback."""

import argparse
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class PreviewHandler(SimpleHTTPRequestHandler):
    """Add single-byte-range requests to the standard static-file handler."""

    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def send_head(self):
        self.byte_range = None
        requested = self.headers.get("Range")
        path = Path(self.translate_path(self.path))
        if not requested or not path.is_file():
            return super().send_head()
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested)
        size = path.stat().st_size
        if match and any(match.groups()) and size:
            first, last = match.groups()
            if first:
                start = int(first)
                end = min(int(last), size - 1) if last else size - 1
            else:
                start, end = max(0, size - int(last)), size - 1
            if 0 <= start <= end < size:
                stream = path.open("rb")
                self.byte_range = start, end
                self.send_response(206)
                self.send_header("Content-Type", self.guess_type(str(path)))
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                self.send_header("Content-Length", str(end - start + 1))
                self.send_header("Last-Modified", self.date_time_string(path.stat().st_mtime))
                self.end_headers()
                return stream
        self.send_response(416)
        self.send_header("Content-Range", f"bytes */{size}")
        self.send_header("Content-Length", "0")
        self.end_headers()
        return None

    def copyfile(self, source, outputfile):
        try:
            if self.byte_range is None:
                return super().copyfile(source, outputfile)
            start, end = self.byte_range
            source.seek(start)
            remaining = end - start + 1
            while remaining:
                chunk = source.read(min(remaining, 256 * 1024))
                if not chunk:
                    break
                outputfile.write(chunk)
                remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            # Browsers cancel the previous range when seeking elsewhere.
            pass


def main():
    here = Path(__file__).resolve()
    default = (
        here.parent if here.name == "preview.py" else here.parents[1] / "artifacts/project-site"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=default)
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not (directory / "index.html").is_file():
        parser.error("Build the website first, or specify a directory containing index.html")
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port), partial(PreviewHandler, directory=str(directory))
    )
    print(f"Project page: http://127.0.0.1:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
