#!/usr/bin/env python3

# ruff: noqa: T201 `print` found

import argparse
import http.server
import os
import socketserver
import sys

PORT = 8000


class GzipHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        path = self.translate_path(self.path)
        if path and path.endswith(".gz"):
            self.send_header("Content-Encoding", "gzip")

        super().end_headers()


def entrypoint():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Root path of the server", default="")

    args = parser.parse_args()

    if args.path:
        os.chdir(os.path.abspath(os.path.expanduser(args.path)))

    socketserver.TCPServer.allow_reuse_address = True

    try:
        with socketserver.TCPServer(("", PORT), GzipHTTPRequestHandler) as httpd:
            print(f"Serving at http://localhost:{PORT}")
            print("Press Ctrl+C to stop the server.")

            httpd.serve_forever()

    except KeyboardInterrupt:
        print("\nShutting down server...")

    return 0


if __name__ == "__main__":
    sys.exit(entrypoint())
