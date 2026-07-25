"""Modern desktop UI — wraps Flask backend in a pywebview native window."""

import sys
import os
import threading

# ── Resolve base path (works for PyInstaller bundle) ─────────────────
def _app_root() -> str:
    if getattr(sys, "frozen", False):
        return sys._MEIPASS  # type: ignore
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def start_gui(host: str = "127.0.0.1", port: int = 0) -> None:
    """Launch the native desktop window."""
    # Lazy imports so CLI-only usage never pays the cost
    import webview  # pywebview
    from pdf2md.web import create_app

    app = create_app()

    # Flask in background thread
    from werkzeug.serving import make_server

    sv = make_server(host, port, app, threaded=True)
    t = threading.Thread(target=sv.serve_forever, daemon=True)
    t.start()

    actual_port = sv.server_port
    url = f"http://{host}:{actual_port}"

    webview.create_window(
        "PDF → Markdown",
        url,
        width=960,
        height=740,
        min_size=(720, 560),
        resizable=True,
        text_select=True,
    )
    webview.start()
    sv.shutdown()
