"""HTTP API + process entry point.

Serves the rendered dashboard PNG and a version number. The Pi polls /version
and downloads /dashboard.png only when the version changes.

Also the container's main process: starts the DB and (later) the photo watcher.
"""
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

import os

from .config import config
from . import store, renderer

app = FastAPI(title="eink-dashboard")


@app.on_event("startup")
def _startup() -> None:
    store.init_db()
    if store.is_empty():
        # Phase 2: seed demo data so the dashboard renders something real.
        store.seed_demo()
        store.bump_version()
    renderer.render()
    # TODO (phase 3): launch the watcher loop in a background thread.


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


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=config.api_port)


if __name__ == "__main__":
    main()
