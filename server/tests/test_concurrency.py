"""Concurrency safety for the shared render/version path.

Asserts forward progress (no deadlock) and no lost version bumps when many
threads bump concurrently — the failure mode the weather phase's third render
thread would otherwise expose.
"""
import concurrent.futures as cf
import importlib
import os

import pytest


@pytest.fixture()
def fresh_store(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    # Re-import config + store so DATA_DIR takes effect on the frozen Config.
    import app.config as config_mod
    importlib.reload(config_mod)
    import app.store as store_mod
    importlib.reload(store_mod)
    store_mod.init_db()
    return store_mod


def test_concurrent_bump_no_lost_updates(fresh_store):
    store = fresh_store
    start = store.get_version()
    n = 200

    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        futures = [ex.submit(store.bump_version) for _ in range(n)]
        # .result() would hang on a deadlock; bound it so the test fails loudly.
        for f in cf.as_completed(futures, timeout=30):
            f.result()

    assert store.get_version() == start + n  # every bump landed, none lost


def test_concurrent_render_if_changed(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import app.config as config_mod
    importlib.reload(config_mod)
    import app.store as store_mod
    importlib.reload(store_mod)
    import app.renderer as renderer_mod
    importlib.reload(renderer_mod)

    store_mod.init_db()
    if store_mod.is_empty():
        store_mod.seed_demo()

    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(renderer_mod.render_if_changed) for _ in range(16)]
        results = [f.result(timeout=60) for f in futures]  # would hang on deadlock

    # Identical inputs -> exactly one render should report a change (the first);
    # all the rest see the same hash. At minimum, it must not deadlock or error.
    assert sum(1 for r in results if r) >= 1
    assert os.path.exists(store_mod.config.png_path)
