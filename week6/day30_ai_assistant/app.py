"""
Week 6 - Day 30 (Option C): Business Knowledge-Base AI Assistant (Flask Web App)
--------------------------------------------------------------------------------
Local development (Windows or Linux):
    python week6/day30_ai_assistant/app.py --check-config
    python week6/day30_ai_assistant/app.py

Production (Render / Gunicorn). --timeout must exceed the worst-case retry
time in pipeline.py (~127 s); Gunicorn's default of 30 s would kill a worker
in the middle of a slow but valid answer:
    gunicorn --chdir week6/day30_ai_assistant --workers 2 --threads 4 \
        --timeout 180 --bind 0.0.0.0:$PORT "app:create_wsgi_app()"
"""

import argparse
import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from collections import deque
from datetime import date
from pathlib import Path
from typing import Callable, Deque, Dict, Optional, Sequence, Tuple

from flask import Flask, jsonify, render_template, request

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import anthropic
from pipeline import (
    API_TIMEOUT_SECONDS,
    CLIENT_MAX_RETRIES,
    FALLBACK_MODEL,
    AssistantConfig,
    ConfigError,
    ModelRoute,
    answer_customer_question,
    load_config,
    load_knowledge_base,
    log_event,
    make_console_unicode_safe,
)

MAX_REQUEST_BYTES = 64 * 1024
RATE_WINDOW_SECONDS = 600


class ChatLimiter:
    """
    Thread-safe spend guard for a public chatbot on the owner's API key.
    - per_ip: max questions per visitor IP in a 10-minute window (0 = off)
    - daily_cap: max paid questions per day for this process (0 = off)
    Counts live in memory per worker process; a restart resets them.
    """

    def __init__(
        self,
        per_ip: int,
        daily_cap: int,
        clock: Callable[[], float] = time.monotonic,
        today: Callable[[], date] = date.today,
    ) -> None:
        self.per_ip = per_ip
        self.daily_cap = daily_cap
        self._clock = clock
        self._today = today
        self._lock = threading.Lock()
        self._hits: Dict[str, Deque[float]] = {}
        self._day = today()
        self._day_count = 0

    def check(self, ip: str) -> Tuple[bool, str]:
        now = self._clock()
        with self._lock:
            if self._today() != self._day:
                self._day, self._day_count = self._today(), 0
            if self.daily_cap and self._day_count >= self.daily_cap:
                return False, "The assistant has reached today's question limit. Please call or WhatsApp us."
            if self.per_ip:
                q = self._hits.setdefault(ip, deque())
                while q and now - q[0] > RATE_WINDOW_SECONDS:
                    q.popleft()
                if len(q) >= self.per_ip:
                    return False, "Too many questions in a short time. Please wait a few minutes."
                q.append(now)
                if len(self._hits) > 5000:  # stop a flood of fake IPs from growing memory
                    for key in [k for k, v in self._hits.items() if not v or now - v[-1] > RATE_WINDOW_SECONDS]:
                        del self._hits[key]
            self._day_count += 1
            return True, ""


def client_ip() -> str:
    """Behind Render's proxy the real visitor is the right-most X-Forwarded-For entry."""
    if os.environ.get("RENDER"):
        forwarded = request.headers.get("X-Forwarded-For", "")
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            return parts[-1]
    return request.remote_addr or "unknown"


def create_app(
    cfg: AssistantConfig,
    client: Optional["anthropic.Anthropic"] = None,
    dry_run: bool = False,
    limiter: Optional[ChatLimiter] = None,
) -> Flask:
    app = Flask(__name__, template_folder=str(APP_DIR / "templates"))
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES

    chunks, doc_names = load_knowledge_base(cfg.docs_dir)
    ai_client = client or (
        None
        if dry_run
        else anthropic.Anthropic(
            api_key=cfg.api_key,
            timeout=API_TIMEOUT_SECONDS,
            max_retries=CLIENT_MAX_RETRIES,
        )
    )
    fallback = FALLBACK_MODEL if cfg.ai_model != FALLBACK_MODEL else None
    route = ModelRoute(model=cfg.ai_model, fallback=fallback)

    app.extensions["kb_chunks"] = chunks
    app.extensions["kb_docs"] = doc_names
    app.extensions["model_route"] = route
    chat_limiter = limiter or ChatLimiter(
        per_ip=cfg.rate_limit_per_10_min,
        daily_cap=cfg.daily_chat_cap,
    )
    app.extensions["chat_limiter"] = chat_limiter

    @app.before_request
    def verify_host_header():
        # Render's health checker connects to the container directly, so its Host
        # header is not the public hostname. /api/health returns no customer data.
        if request.path == "/api/health":
            return None
        hostname = (request.host or "").rsplit(":", 1)[0].strip("[]").lower()
        if hostname not in cfg.allowed_hosts:
            return jsonify({"ok": False, "error": "Host not allowed."}), 403
        return None

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        return resp

    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html", cfg=cfg, doc_names=doc_names)

    @app.route("/api/health", methods=["GET"])
    def health():
        model, switched_from = route.snapshot()
        return jsonify(
            {
                "ok": True,
                "company": cfg.company_name,
                "model": model,
                "switched_from": switched_from,
                "docs_loaded": len(doc_names),
                "chunks_indexed": len(chunks),
            }
        )

    @app.route("/api/docs", methods=["GET"])
    def list_docs():
        return jsonify({"ok": True, "documents": doc_names, "chunks": len(chunks)})

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"ok": False, "error": "Invalid JSON body. Reload the page and retry."}), 400

        allowed, reason = chat_limiter.check(client_ip())
        if not allowed:
            log_event("WARNING", "rate_limited")
            return jsonify({"ok": False, "error": reason}), 429

        res = answer_customer_question(
            raw_question=payload.get("question"),
            chunks=chunks,
            cfg=cfg,
            history=payload.get("history"),
            client=ai_client,
            route=route,
            dry_run=dry_run,
        )
        if not res.ok:
            return jsonify({"ok": False, "error": res.error}), res.status_code

        body = {"ok": True, "reply": res.reply, "truncated": res.truncated}
        if cfg.show_telemetry:
            # Demo footer data. Off in production so customers never see costs or
            # model names; the owner still has all of it in logs/app.log.
            body.update(
                {
                    "sources": res.sources,
                    "model": res.model,
                    "switched_from": res.switched_from,
                    "input_tokens": res.input_tokens,
                    "output_tokens": res.output_tokens,
                    "cost_kes": str(res.cost_kes),
                    "latency_ms": res.latency_ms,
                }
            )
        return jsonify(body), 200

    @app.errorhandler(404)
    def handle_404(_err):
        return jsonify({"ok": False, "error": "Endpoint not found."}), 404

    @app.errorhandler(405)
    def handle_405(_err):
        return jsonify({"ok": False, "error": "HTTP method not allowed."}), 405

    @app.errorhandler(413)
    def handle_413(_err):
        return jsonify({"ok": False, "error": "Request is too large. Shorten your message."}), 413

    @app.errorhandler(429)
    def handle_429(_err):
        return jsonify({"ok": False, "error": "Too many requests. Please wait a few minutes."}), 429

    @app.errorhandler(500)
    def handle_500(_err):
        return jsonify({"ok": False, "error": "Internal server error. Try again shortly."}), 500

    return app


def create_wsgi_app() -> Flask:
    """Entrypoint for Gunicorn on Render (start command in the module docstring)."""
    cfg = load_config(require_api_key=True)
    return create_app(cfg)


def port_problem(port: int, host: str = "127.0.0.1") -> Optional[str]:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return (
                f"Port {port} is already in use. Close the existing assistant window or set "
                "PORT=5050 in .env."
            )
    except OSError:
        pass
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        probe.bind((host, port))
    except OSError as err:
        return f"Port {port} cannot be bound ({err.strerror or err}). Set PORT=5050 in .env."
    finally:
        probe.close()
    return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    make_console_unicode_safe()
    parser = argparse.ArgumentParser(description="Day 30 Business AI Assistant Server.")
    parser.add_argument("--env", type=Path, default=None, help="Path to .env config file.")
    parser.add_argument("--check-config", action="store_true", help="Validate config and docs, then exit.")
    parser.add_argument("--dry-run", action="store_true", help="Run UI offline without API calls.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser tab automatically.")
    args = parser.parse_args(argv)

    try:
        cfg = load_config(env_path=args.env, require_api_key=not args.dry_run)
        chunks, doc_names = load_knowledge_base(cfg.docs_dir)
    except (ConfigError, FileNotFoundError) as err:
        print(f"\n[CONFIGURATION ERROR]\n{err}")
        return 1

    if args.check_config:
        print(f"[OK] {cfg.company_name} ({cfg.business_location})")
        print(f"     Docs loaded : {len(doc_names)} ({', '.join(doc_names)}) | {len(chunks)} chunks")
        print(f"     Model       : {cfg.ai_model}")
        print(f"     Citations   : {'on' if cfg.show_citations else 'off'} | "
              f"Cost/model footer: {'on' if cfg.show_telemetry else 'off'}")
        print(f"     Address     : http://{cfg.host}:{cfg.port}")
        return 0

    if cfg.host in ("127.0.0.1", "localhost"):
        problem = port_problem(cfg.port, cfg.host)
        if problem:
            print(f"\n[STARTUP ERROR] {problem}")
            return 1

    url = f"http://{cfg.host}:{cfg.port}"
    print("=" * 64)
    print(f"  {cfg.company_name} - 24/7 Business AI Assistant")
    print(f"  Docs indexed : {len(doc_names)} files ({len(chunks)} chunks)")
    print(f"  Open browser : {url}")
    print("  Press Ctrl+C to stop.")
    print("=" * 64)
    log_event("INFO", f"server_start company={cfg.company_name} docs={len(doc_names)} port={cfg.port}")

    app = create_app(cfg, dry_run=args.dry_run)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    if not args.no_browser and cfg.host in ("127.0.0.1", "localhost"):
        threading.Timer(1.0, webbrowser.open, args=[url]).start()

    try:
        app.run(host=cfg.host, port=cfg.port, debug=False, use_reloader=False, threaded=True)
    except KeyboardInterrupt:
        print("\n[STOPPED] Assistant closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
