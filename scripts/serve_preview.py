#!/usr/bin/env python3
"""Serve an optional CAD workbench with token-protected comment mutations."""

from __future__ import annotations

import argparse
import functools
import hmac
import http.server
import json
import math
import os
import re
import socket
import secrets
import subprocess
import sys
import time
from urllib.parse import quote, unquote
import urllib.request
import webbrowser
from pathlib import Path

REVIEW_TOKEN_ENV = "FUNCTIONAL_FDM_REVIEW_TOKEN"


class PreviewHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(
        self,
        *args: object,
        progress_path: Path,
        manifest_path: Path,
        mutation_token: str,
        **kwargs: object,
    ) -> None:
        self.progress_path = progress_path
        self.manifest_path = manifest_path
        self.mutation_token = mutation_token
        super().__init__(*args, **kwargs)

    def send_json(self, status: int, value: object) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()

    def do_POST(self) -> None:
        if self.path.partition("?")[0] != "/api/review-comments":
            self.send_json(404, {"ok": False, "error": "Unknown endpoint."})
            return
        if not self.authorized_mutation():
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 16_384:
                raise ValueError("Comment request must be between 1 byte and 16 KB.")
            value = json.loads(self.rfile.read(length))
            if not isinstance(value, dict):
                raise ValueError("Comment request must be a JSON object.")
            message = value.get("message")
            part = value.get("part")
            position = value.get("position_mm")
            if not isinstance(message, str) or not message.strip() or len(message) > 2_000:
                raise ValueError("Comment text must contain 1 to 2,000 characters.")
            if not isinstance(part, str) or not part:
                raise ValueError("A model part is required.")
            if (
                not isinstance(position, list)
                or len(position) != 3
                or any(not isinstance(item, (int, float)) or not math.isfinite(item) for item in position)
            ):
                raise ValueError("position_mm must contain three finite numbers.")
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            part_names = {
                item.get("name")
                for collection in (manifest.get("parts", []), manifest.get("references", []))
                for item in collection
                if isinstance(item, dict)
            }
            if part not in part_names:
                raise ValueError(f"Unknown model part: {part}")
            command = [
                sys.executable,
                str(Path(__file__).with_name("update_progress.py")),
                "comment-add",
                str(self.progress_path),
                "--part",
                part,
                "--position",
                *(str(item) for item in position),
                "--message",
                message.strip(),
            ]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip() or "Unable to record comment."
                raise ValueError(detail)
            self.send_json(201, {"ok": True})
        except (ValueError, json.JSONDecodeError, OSError) as error:
            self.send_json(400, {"ok": False, "error": str(error)})

    def do_DELETE(self) -> None:
        prefix = "/api/review-comments/"
        path = self.path.partition("?")[0]
        if not path.startswith(prefix):
            self.send_json(404, {"ok": False, "error": "Unknown endpoint."})
            return
        if not self.authorized_mutation():
            return
        identifier = unquote(path[len(prefix):])
        if not identifier or "/" in identifier:
            self.send_json(400, {"ok": False, "error": "A comment id is required."})
            return
        try:
            command = [
                sys.executable,
                str(Path(__file__).with_name("update_progress.py")),
                "comment-remove",
                str(self.progress_path),
                "--id",
                identifier,
            ]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip() or "Unable to remove comment."
                raise ValueError(detail)
            self.send_json(200, {"ok": True})
        except (ValueError, OSError) as error:
            self.send_json(400, {"ok": False, "error": str(error)})

    def authorized_mutation(self) -> bool:
        supplied = self.headers.get("Authorization", "")
        expected = f"Bearer {self.mutation_token}"
        if not self.mutation_token or not hmac.compare_digest(supplied, expected):
            self.send_json(401, {"ok": False, "error": "A valid review session token is required."})
            return False
        return True

    def log_message(self, format: str, *args: object) -> None:
        # Legacy query-token URLs can reach the server once before the browser
        # migrates them. Never preserve that token in access logs.
        redacted = tuple(
            re.sub(r"([?&]token=)[^&#\s]+", r"\1[redacted]", item)
            if isinstance(item, str)
            else item
            for item in args
        )
        super().log_message(format, *redacted)

    def end_headers(self) -> None:
        # Review builds intentionally reuse stable model filenames. Disable
        # caching for every response so a normal refresh cannot mix a new
        # manifest with an older STL, STEP, font, or compiled asset.
        self.send_header(
            "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
        )
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


class PreviewServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def reachable_hosts(bind_host: str) -> list[str]:
    if bind_host in {"127.0.0.1", "localhost", "::1"} or bind_host.startswith("127."):
        return ["127.0.0.1"]
    if bind_host not in {"0.0.0.0", "::"}:
        return [bind_host]
    hosts: set[str] = set()
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        hosts.add(probe.getsockname()[0])
        probe.close()
    except OSError:
        pass
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            hosts.add(item[4][0])
    except OSError:
        pass
    return sorted(
        address
        for address in hosts
        if address and not address.startswith(("127.", "169.254.")) and address != "0.0.0.0"
    )


def resolve_preview(path: Path) -> tuple[Path, Path, str]:
    preview = path.resolve()
    if not (preview / "index.html").is_file() and (preview / "preview" / "index.html").is_file():
        preview = preview / "preview"
    if not (preview / "index.html").is_file():
        raise ValueError("Preview folder does not contain index.html.")
    root = preview.parent
    return preview, root, f"/{preview.name}/"


def build_review_urls(base_urls: list[str], token: str) -> list[str]:
    """Return browser-local capability URLs; fragments never reach HTTP."""
    return [f"{url}#token={quote(token, safe='')}" for url in base_urls]


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def daemonize(args: argparse.Namespace, preview: Path, token: str) -> int:
    info_file = (args.info_file or preview.parent / ".preview-server.json").resolve()
    pid_file = (args.pid_file or preview.parent / ".preview-server.pid").resolve()
    log_file = (args.log_file or preview.parent / ".preview-server.log").resolve()
    for stale in (info_file, pid_file):
        stale.unlink(missing_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        str(preview),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--daemon-child",
        "--info-file",
        str(info_file),
        "--pid-file",
        str(pid_file),
        "--log-file",
        str(log_file),
    ]
    child_environment = dict(os.environ)
    child_environment[REVIEW_TOKEN_ENV] = token
    with log_file.open("ab", buffering=0) as log:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
            env=child_environment,
        )
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Preview server exited during startup. Inspect {log_file}.")
        if info_file.is_file():
            info = json.loads(info_file.read_text(encoding="utf-8"))
            base_urls = info.get("base_urls", [])
            if base_urls:
                try:
                    with urllib.request.urlopen(base_urls[0], timeout=2) as response:
                        if response.status == 200:
                            review_urls = build_review_urls(base_urls, token)
                            result = {
                                **info,
                                "review_urls": review_urls,
                                "urls": review_urls,
                                "durable": True,
                                "log_file": str(log_file),
                                "pid_file": str(pid_file),
                            }
                            if args.open:
                                webbrowser.open(review_urls[0])
                            print(json.dumps(result, indent=2), flush=True)
                            return 0
                except OSError:
                    pass
        time.sleep(0.1)
    process.terminate()
    raise RuntimeError(f"Preview server did not become reachable. Inspect {log_file}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("preview", type=Path)
    parser.add_argument("--host", default="127.0.0.1", help="Bind address. Defaults to loopback only.")
    parser.add_argument("--lan", action="store_true", help="Explicitly bind to 0.0.0.0 for trusted-LAN review.")
    parser.add_argument("--port", type=int, default=0, help="TCP port. The default selects a free port.")
    parser.add_argument("--open", action="store_true", help="Open the tokenized review URL in a browser.")
    parser.add_argument("--daemon", action="store_true", help="Start a detached server that survives the calling agent process.")
    parser.add_argument("--info-file", type=Path, help="JSON file for server address and reachable URLs.")
    parser.add_argument("--pid-file", type=Path, help="File that records the detached server PID.")
    parser.add_argument("--log-file", type=Path, help="File for detached server logs.")
    parser.add_argument("--daemon-child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.lan:
        if args.host != "127.0.0.1":
            raise ValueError("Use either --lan or --host for network exposure, not both.")
        args.host = "0.0.0.0"
    token = os.environ.get(REVIEW_TOKEN_ENV) or secrets.token_urlsafe(24)
    preview, root, url_path = resolve_preview(args.preview)
    if args.daemon:
        return daemonize(args, preview, token)

    # Keep the capability in memory after startup; mutation helper processes
    # must not inherit it from the server environment.
    os.environ.pop(REVIEW_TOKEN_ENV, None)

    hosts = reachable_hosts(args.host)
    if not hosts:
        raise ValueError("No reachable address is available for this bind host.")
    handler = functools.partial(
        PreviewHandler,
        directory=str(root),
        progress_path=preview.parent / "progress.json",
        manifest_path=preview / "manifest.json",
        mutation_token=token,
    )
    server = PreviewServer((args.host, args.port), handler)
    port = int(server.server_address[1])
    base_urls = [f"http://{host}:{port}{url_path}" for host in hosts]
    review_urls = build_review_urls(base_urls, token)
    lan_mode = args.host not in {"127.0.0.1", "localhost", "::1"} and not args.host.startswith("127.")
    safe_info = {
        "host": args.host,
        "port": port,
        "pid": os.getpid(),
        "preview": str(preview),
        "progress": str(preview.parent / "progress.json"),
        "base_urls": base_urls,
        "lan_mode": lan_mode,
    }
    if lan_mode:
        safe_info["warning"] = "LAN review is active. Anyone with the complete review URL can change comments."
    if args.info_file:
        write_json(args.info_file.resolve(), safe_info)
    if args.pid_file:
        args.pid_file.parent.mkdir(parents=True, exist_ok=True)
        args.pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")
    output = safe_info if args.daemon_child else {
        **safe_info,
        "review_urls": review_urls,
        # Compatibility for callers that consumed the former `urls` field.
        "urls": review_urls,
    }
    print(json.dumps(output), flush=True)
    if args.open:
        webbrowser.open(review_urls[0])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, OSError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, indent=2), file=sys.stderr)
        sys.exit(2)
