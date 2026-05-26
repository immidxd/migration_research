#!/usr/bin/env python3
"""PyWebview desktop entrypoint for the Migrations research tool.

Mirrors the BMS launcher pattern: start uvicorn in a thread, wait for
/api/health, then open a window pointing at the served frontend.
"""
from __future__ import annotations

import http.client
import logging
import shutil
import sys
import threading
import time
from pathlib import Path

import uvicorn
import webview
from dotenv import load_dotenv

from backend.app.settings import get_settings


def clear_webkit_cache() -> None:
    """Nuke pywebview's WKWebView cache so a fresh build of the React bundle
    is always loaded — otherwise the old main.[hash].js can stick around and
    UI changes appear to "not deploy"."""
    candidates = [
        Path.home() / "Library/WebKit/com.apple.WebKit.WebContent",
        Path.home() / "Library/Caches/com.apple.WebKit.WebContent",
        Path.home() / "Library/Caches/pywebview",
        Path.home() / "Library/WebKit/Default",
    ]
    for p in candidates:
        if p.exists():
            try:
                shutil.rmtree(p)
                logger_clear = logging.getLogger("migrations.desktop")
                logger_clear.info("cleared WebKit cache at %s", p)
            except Exception as e:
                logging.getLogger("migrations.desktop").warning(
                    "could not clear %s: %s", p, e
                )


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("migrations.desktop")


def start_backend(host: str, port: int) -> None:
    try:
        uvicorn.run(
            "backend.app.main:app",
            host=host,
            port=port,
            log_level=get_settings().log_level,
        )
    except Exception:
        logger.exception("Failed to start backend")
        sys.exit(1)


def wait_for_backend(host: str, port: int, retries: int = 40, delay: float = 0.5) -> bool:
    probe_host = "127.0.0.1" if host in {"0.0.0.0", "localhost"} else host
    for i in range(retries):
        try:
            conn = http.client.HTTPConnection(probe_host, port, timeout=2)
            conn.request("GET", "/api/health")
            resp = conn.getresponse()
            conn.close()
            if resp.status == 200:
                logger.info("Backend is up")
                return True
        except Exception:
            pass
        logger.info("Waiting for backend (%s/%s)", i + 1, retries)
        time.sleep(delay)
    return False


def main() -> None:
    load_dotenv()
    settings = get_settings()
    clear_webkit_cache()

    backend_thread = threading.Thread(
        target=start_backend, args=(settings.host, settings.port), daemon=True
    )
    backend_thread.start()

    if not wait_for_backend(settings.host, settings.port):
        logger.error("Backend did not become healthy in time")
        sys.exit(1)

    url = f"http://127.0.0.1:{settings.port}"
    logger.info("Opening window at %s", url)
    webview.create_window(
        "Migrations Research",
        url,
        width=1440,
        height=900,
        min_size=(1024, 700),
    )
    # debug=True exposes WKWebView's developer tools: right-click in the
    # window → "Inspect Element" → Console tab to see JS errors and the
    # network panel. Essential while diagnosing rendering issues.
    webview.start(debug=True)


if __name__ == "__main__":
    main()
