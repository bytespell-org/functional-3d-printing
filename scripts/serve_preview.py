#!/usr/bin/env python3
"""Serve an interactive preview folder for local or shared review."""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socket
import sys
import webbrowser
from pathlib import Path


def reachable_hosts(bind_host: str) -> list[str]:
    if bind_host not in {"0.0.0.0", "::"}:
        return [bind_host]
    hosts = {"127.0.0.1"}
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = item[4][0]
            if address and not address.startswith("127."):
                hosts.add(address)
    except OSError:
        pass
    return sorted(hosts, key=lambda value: (value.startswith("127."), value))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("preview", type=Path)
    parser.add_argument("--host", default="127.0.0.1", help="Bind address. Use 0.0.0.0 only when network sharing is intended.")
    parser.add_argument("--port", type=int, default=8765, help="TCP port. Use 0 to select a free port.")
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--info-file", type=Path, help="Optional JSON file for server address and reachable URLs.")
    args = parser.parse_args()
    if not (args.preview / "index.html").is_file():
        raise ValueError("Preview folder does not contain index.html.")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(args.preview))
    server = http.server.ThreadingHTTPServer((args.host, args.port), handler)
    port = int(server.server_address[1])
    urls = [f"http://{host}:{port}/" for host in reachable_hosts(args.host)]
    info = {"host": args.host, "port": port, "preview": str(args.preview.resolve()), "urls": urls}
    if args.info_file:
        args.info_file.parent.mkdir(parents=True, exist_ok=True)
        args.info_file.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(info), flush=True)
    if args.open:
        webbrowser.open(urls[0])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
