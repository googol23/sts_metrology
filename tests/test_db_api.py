from __future__ import annotations

import os
import pathlib
import sys

import pytest

# ---------------------------------------------------------------------------
# Make sure we can import db_api/db_api.py as module "db_api"
# ---------------------------------------------------------------------------

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "db_api"
sys.path.insert(0, str(MODULE_DIR))

import db_api as mod  # this imports db_api/db_api.py


def _save_env(keys: list[str]) -> dict[str, str | None]:
    """Helper to snapshot selected env vars."""
    return {k: os.environ.get(k) for k in keys}


def _restore_env(snapshot: dict[str, str | None]) -> None:
    """Helper to restore env vars from a snapshot."""
    for k, v in snapshot.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


# ---------------------------------------------------------------------------
# Tests for get_conn_from_env
# ---------------------------------------------------------------------------


def test_get_conn_from_env_missing_password_raises():
    """
    If PGPASSWORD is missing, get_conn_from_env must raise RuntimeError.
    This does NOT touch psycopg2.connect at all.
    """
    keys = ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]
    snapshot = _save_env(keys)

    try:
        # Set all but password
        os.environ["PGHOST"] = "pgsql.gsi.de"
        os.environ["PGPORT"] = "8646"
        os.environ["PGDATABASE"] = "dtl"
        os.environ["PGUSER"] = "dtl_read"
        os.environ.pop("PGPASSWORD", None)

        with pytest.raises(RuntimeError) as excinfo:
            mod.get_conn_from_env()

        msg = str(excinfo.value)
        assert "PGPASSWORD" in msg
    finally:
        _restore_env(snapshot)


def test_get_conn_from_env_real_connection_or_skip():
    """
    Use the real psycopg2 connection if PGPASSWORD is available.

    - If PGPASSWORD is not set in the environment, we SKIP the test.
    - Otherwise we call get_conn_from_env() and assert the connection is open.
    """
    if os.environ.get("PGPASSWORD") is None:
        pytest.skip("PGPASSWORD not set; skipping real DB connection test")

    conn = mod.get_conn_from_env()
    try:
        # psycopg2 connection: closed==0 means open
        assert conn is not None
        assert getattr(conn, "closed", 1) == 0
    finally:
        conn.close()
