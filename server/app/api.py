"""HTTP API + process entry point.

Serves the rendered dashboard PNG and a version number. The Pi polls /version
and downloads /dashboard.png only when the version changes.

Also the container's main process: starts the DB and (later) the photo watcher.
"""
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

import os

from .config import config
from . import store, renderer, daily_tick

app = FastAPI(title="eink-dashboard")


@app.on_event("startup")
def _startup() -> None:
    store.init_db()
    if store.is_empty():
        # Phase 2: seed demo data so the dashboard renders something real.
        store.seed_demo()
    # Renders and bumps the version + seeds the png hash for change detection.
    renderer.render_if_changed()
    # Core always-on tick: advances the date and activates Sunday-review mode even
    # with every integration disabled. Core, so started here (not in main.py).
    daily_tick.start_background()
    # Note: the Meta-glasses photo watcher is started by the composition root
    # (app/main.py), not here — core stays independent of the glasses package.


@app.get("/")
def root() -> RedirectResponse:
    # Bare host → the dashboard image, so browsing the server shows something useful.
    return RedirectResponse(url="/dashboard.png")


@app.get("/version")
def version() -> JSONResponse:
    return JSONResponse({"version": store.get_version()})


@app.get("/dashboard.png")
def dashboard_png() -> FileResponse:
    if not os.path.exists(config.png_path):
        renderer.render()
    return FileResponse(config.png_path, media_type="image/png")


@app.get("/healthz")
def healthz() -> JSONResponse:
    return JSONResponse({"ok": True})


# TODO (phase 4): POST /bot webhook → app.bot.handle_message


def run() -> None:
    """Serve the core API (no glasses integration). See app/main.py to wire both."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=config.api_port)


if __name__ == "__main__":
    run()
