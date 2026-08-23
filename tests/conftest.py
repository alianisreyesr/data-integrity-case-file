"""Shared fixtures: isolated DB path + reset shared aiosqlite connection."""
import asyncio
import os

import pytest

os.environ.setdefault("API_KEY", "test-api-key")


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)

    import app.database as db_mod
    import app.security as security_mod

    security_mod.API_KEY = "test-api-key"

    async def _reset():
        await db_mod.disconnect()

    try:
        asyncio.run(_reset())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_reset())
        loop.close()

    db_mod.DB_PATH = db_path
    db_mod._db = None
    db_mod.init_db_sync()

    yield

    try:
        asyncio.run(_reset())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_reset())
        loop.close()
    db_mod._db = None
