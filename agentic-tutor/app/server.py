"""HTTP server: transport layer only.

Serves the chat UI from ../static and exposes a small JSON API:
  POST /api/chat     {session_id, message} -> {reply, phase, error, ...}
  GET  /api/profile  -> the stored learner profile (for the profile panel)

All teaching decisions live in tutor.py. Run with:
  python -m app.server            (from the agentic-tutor directory)
Environment:
  PORT            - default 8000
  PROFILE_PATH    - default data/profile.json
  LLM_API_KEY etc - see app/llm.py
  MOCK_LLM=1      - offline scripted mock, no API key needed
"""

from __future__ import annotations

import json
import os
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .llm import build_default_client
from .memory import ProfileStore
from .tutor import TutorEngine

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DEFAULT_PROFILE_PATH = BASE_DIR / "data" / "profile.json"

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}


def make_engine() -> TutorEngine:
    profile_path = os.environ.get("PROFILE_PATH") or str(DEFAULT_PROFILE_PATH)
    return TutorEngine(build_default_client(), ProfileStore(profile_path))


class ChatHandler(BaseHTTPRequestHandler):
    engine: TutorEngine  # set by run()

    server_version = "AgenticTutor/0.1"

    # Quieten default logging; keep errors visible.
    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib name
        pass

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            return None

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        if self.path == "/api/profile":
            self._send_json(200, self.engine.store.load())
            return
        path = "/index.html" if self.path in ("/", "") else self.path.split("?")[0]
        # Prevent path traversal: resolve and require containment.
        candidate = (STATIC_DIR / path.lstrip("/")).resolve()
        if not str(candidate).startswith(str(STATIC_DIR.resolve())) or not candidate.is_file():
            self._send_json(404, {"error": "not found"})
            return
        body = candidate.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type", _CONTENT_TYPES.get(candidate.suffix, "application/octet-stream")
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        if self.path != "/api/chat":
            self._send_json(404, {"error": "not found"})
            return
        body = self._read_json_body()
        if body is None or not isinstance(body.get("message"), str):
            self._send_json(400, {"error": "expected JSON with a 'message' string"})
            return
        session_id = body.get("session_id") or uuid.uuid4().hex
        try:
            result = self.engine.handle_message(session_id, body["message"])
        except Exception:  # last-resort guard: never leak a stack trace to the UI
            self._send_json(
                200,
                {
                    "session_id": session_id,
                    "reply": "Something went wrong on my side. Your session is intact — please try again.",
                    "error": True,
                },
            )
            return
        result["session_id"] = session_id
        self._send_json(200, result)


def run(port: int | None = None) -> None:
    port = port or int(os.environ.get("PORT", "8000"))
    ChatHandler.engine = make_engine()
    server = ThreadingHTTPServer(("127.0.0.1", port), ChatHandler)
    mode = "mock LLM (offline)" if os.environ.get("MOCK_LLM") == "1" else "live LLM"
    print(f"Tutor running on http://127.0.0.1:{port}  [{mode}]")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
