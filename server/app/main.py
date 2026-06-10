"""Composition root — wires the core dashboard together with the Meta AI
glasses integration and runs the server.

This is the ONE place that depends on both `app.api` (core) and `app.glasses`.
The core never imports `glasses`; the integration plugs in here, so it can be
swapped or removed by editing only this file.
"""
import logging

import uvicorn

from .api import app
from .config import config
from .glasses import watcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@app.on_event("startup")
def _start_glasses_watcher() -> None:
    # Runs after the core startup hook (DB init + first render).
    watcher.start_background()


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=config.api_port)


if __name__ == "__main__":
    main()
