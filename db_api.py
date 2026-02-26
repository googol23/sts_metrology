"""
inspect_dtl_db.py

Utilities to inspect the STS-related tables in the DTL PostgreSQL database.

Features:
- Connects to the DTL DB in read-only mode using psycopg2.
- Lists tables and columns in a given schema.
- Prints column info and sample rows for a given table.
- Ladder utilities:
    * get_ladder_modules: return ordered module names for a ladder.
    * get_module_sensor: map a module ID to its sensor name.
    * get_sensors_size: compute ladder length in Y including sensor overlap.
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np

# --- Constants ----------------------------------------------------------------

SENSOR_OVERLAP_MM: float = 4.2  # mm

STS_SENSOR_SIZE: dict[str, tuple[float, float]] = {
    "0": (62, 22),
    "1": (62, 22),
    "2": (62, 42),
    "3": (62, 62),
    "4": (62, 124),
}


# --- Database connection helpers ----------------------------------------------
def get_conn_from_env() -> psycopg2.extensions.connection:
    """
    Create a read-only PostgreSQL connection using environment variables.

    Environment variables used:
        PGHOST     (default: "pgsql.gsi.de")
        PGPORT     (default: "8646")
        PGDATABASE (default: "dtl")
        PGUSER     (default: "dtl_read")
        PGPASSWORD (no default – must be set)

    Returns
    -------
    psycopg2.extensions.connection
        An open psycopg2 connection using RealDictCursor.

    Raises
    ------
    RuntimeError
        If required environment variables (especially PGPASSWORD) are missing.
    """
    # env = {
    #     "host": os.getenv("PGHOST", "pgsql.gsi.de"),
    #     "port": os.getenv("PGPORT", "8646"),
    #     "dbname": os.getenv("PGDATABASE", "dtl"),
    #     "user": os.getenv("PGUSER", "dtl_read"),
    #     "password": os.getenv("PGPASSWORD"),
    # }
    env = {
        "host": "pgsql.gsi.de",
        "port": "8646",
        "dbname": "dtl",
        "user": "dtl_read",
        "password": "SFVZkz3FsuDRBfpZ5OVc",
    }

    missing = [k for k, v in env.items() if not v]
    if missing:
        # Map internal keys to standard PG* names for the error message.
        key_map = {
            "host": "PGHOST",
            "port": "PGPORT",
            "dbname": "PGDATABASE",
            "user": "PGUSER",
            "password": "PGPASSWORD",
        }
        missing_env = [key_map[k] for k in missing]
        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing_env)
            + ". Please set them and re-run."
        )

    conn = psycopg2.connect(
        host=env["host"],
        port=env["port"],
        dbname=env["dbname"],
        user=env["user"],
        password=env["password"],
        cursor_factory=RealDictCursor,
        connect_timeout=10,
    )
    return conn


# --- Introspection utilities --------------------------------------------------
def list_tables(conn: psycopg2.extensions.connection, schema: str = "public") -> List[str]:
    """
    List all base tables in the given schema.

    Parameters
    ----------
    conn
        Open psycopg2 connection.
    schema
        Schema name. Default: "public".

    Returns
    -------
    list of str
        Fully qualified table names, e.g. "public.sts_module".
    """
    sql = """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema = %s AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (schema,))
        return [f"{r['table_schema']}.{r['table_name']}" for r in cur.fetchall()]

def list_columns_for_table(
    conn: psycopg2.extensions.connection,
    schema: str,
    table: str,
) -> List[dict]:
    """
    List columns and data types for the given table.

    Parameters
    ----------
    conn
        Open psycopg2 connection.
    schema
        Schema name.
    table
        Table name (without schema).

    Returns
    -------
    list of dict
        Each dict has keys: "column_name", "data_type".
    """
    sql = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (schema, table))
        return cur.fetchall()

def inspect_table(
    table_name: str = "public.sts_sensor",
    limit: int = 10,
    conn: Optional[psycopg2.extensions.connection] = None,
) -> None:
    """
    Print column info and a few example rows from the given table.

    Parameters
    ----------
    table_name
        Fully qualified table name, e.g. "public.sts_module".
    limit
        Maximum number of rows to print.
    conn
        Optional existing database connection. If None, a new connection
        is created and closed inside this function.
    """
    close_conn = False
    if conn is None:
        conn = get_conn_from_env()
        close_conn = True

    schema, _, table = table_name.partition(".")
    if not schema or not table:
        raise ValueError(f"table_name must be 'schema.table', got: {table_name!r}")

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Show schema (column names + types)
            cur.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position;
                """,
                (schema, table),
            )

            print(f"Columns in {schema}.{table}:")
            for row in cur.fetchall():
                print(f"  {row['column_name']:25} {row['data_type']}")

            # 2. Show sample data
            cur.execute(f"SELECT * FROM {schema}.{table} LIMIT %s;", (limit,))
            rows = cur.fetchall()
            print(f"\nSample {min(limit, len(rows))} row(s):")
            for r in rows:
                print(r)
    finally:
        if close_conn:
            conn.close()


# --- Ladder / module helpers --------------------------------------------------

def sort_ladder_modules(modules: List[str]) -> List[str]:
    """
    Sort ladder modules from top to bottom.

    Naming convention (assumed):
      - modules[5] = 'T' → top half (sorted descending by position)
      - modules[5] = 'B' → bottom half (sorted ascending by position)
      - position is a single digit at index 6
      - malformed entries go last, order among them preserved

    Parameters
    ----------
    modules
        List of module identifiers.

    Returns
    -------
    list of str
        Sorted module identifiers.
    """

    def custom_key(m: str) -> tuple[int, int]:
        side = m[5] if len(m) > 5 else ""
        try:
            pos = int(m[6]) if len(m) > 6 else 100
        except ValueError:
            pos = 100

        if side == "T":
            return (0, -pos)  # top half, reversed
        elif side == "B":
            return (1, pos)   # bottom half, normal
        else:
            return (2, 0)     # malformed → last

    return sorted(modules, key=custom_key)

def get_ladder_modules(
    ladder_id: str,
    conn: Optional[psycopg2.extensions.connection] = None,
    sorted: bool = True,
) -> List[str]:
    """
    Return list of module names for the given ladder_id.

    The query picks the maximum version digit inside the module name and
    reconstructs the name with that version.

    Parameters
    ----------
    ladder_id
        Ladder identifier (sts_module.ladder_name).
    conn
        Optional open connection. If None, a new connection is created
        and closed inside this function.
    sorted
        If True, modules are sorted top-to-bottom using sort_ladder_modules.

    Returns
    -------
    list of str
        Module names for this ladder.
    """
    close_conn = False
    if conn is None:
        conn = get_conn_from_env()
        close_conn = True

    sql = """
        SELECT
            MAX(substring(name, 8, 1)) AS version,
            overlay(name, '0', 8, 1)   AS name_new
        FROM sts_module
        WHERE ladder_name = %s
        GROUP BY name_new;
    """

    try:
        with conn.cursor() as cur:
            cur.execute(sql, (ladder_id,))
            rows = cur.fetchall()

        modules: List[str] = []
        for r in rows:
            base = r["name_new"]
            version = r["version"]
            # Replace the version digit at index 7 with the actual version.
            modules.append(base[:7] + version + base[8:])

        return sort_ladder_modules(modules) if sorted else modules
    finally:
        if close_conn:
            conn.close()

def get_module_sensor(
    module_id: str,
    conn: Optional[psycopg2.extensions.connection] = None,
) -> Optional[str]:
    """
    Return sensor name for a given module ID.

    Parameters
    ----------
    module_id
        Module identifier (sts_module.name).
    conn
        Optional open connection. If None, a new connection is created
        and closed inside this function.

    Returns
    -------
    str or None
        Sensor name if found, otherwise None.
    """
    close_conn = False
    if conn is None:
        conn = get_conn_from_env()
        close_conn = True

    sql = """
        SELECT sensor_name
        FROM public.sts_module
        WHERE name = %s;
    """

    try:
        with conn.cursor() as cur:
            cur.execute(sql, (module_id,))
            row = cur.fetchone()
            return row["sensor_name"] if row else None
    finally:
        if close_conn:
            conn.close()

def get_sensors_size(
    ladder_id: str,
    conn: psycopg2.extensions.connection | None = None,
) -> list[tuple[float, float]]:
    """
    Return the list of (X, Y) sensor sizes (in mm) for all modules in a ladder.

    Returns
    -------
    list[tuple[float, float]]
        Each tuple is (size_x_mm, size_y_mm) for one sensor, in ladder order.
    """
    close_conn = False
    if conn is None:
        from .db_api import get_conn_from_env  # avoid circular import
        conn = get_conn_from_env()
        close_conn = True

    sql = """
        SELECT get_sensor_size_mm(sts_module.sensor_name::smallint) AS size_xy
        FROM public.sts_module
        WHERE ladder_name = %s;
    """

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (ladder_id,))
            rows = cur.fetchall()

        sizes: list[tuple[float, float]] = []

        for row in rows:
            # Example assumption:
            # DB returns something like "62x42" or "(62,42)" or "XY=62,42"
            # Your earlier code extracted Y via size[3:], but we now parse both.
            raw = str(row["size_xy"]).strip()

            # Try to extract numbers in a robust but simple way
            nums = [float(n) for n in "".join(
                ch if (ch.isdigit() or ch == '.') else " "
                for ch in raw
            ).split()]

            if len(nums) != 2:
                raise ValueError(f"Could not parse sensor size from DB string: {raw!r}")

            sx, sy = nums
            sizes.append((sx, sy))

        return sizes

    finally:
        if close_conn:
            conn.close()

def compute_ladder_size_xy(
    ladder_id: str,
    conn=None,
    overlap_mm: float | None = SENSOR_OVERLAP_MM,
) -> tuple[float, float]:
    """
    Compute the ladder size in X and Y (in mm) for the given ladder.

    This function:
      - fetches sensor sizes from the DB
      - sums Y with overlap correction
      - determines X from the widest sensor

    Returns
    -------
    (size_x_mm, size_y_mm)
        Tuple of floats representing the ladder width (X) and height (Y).
    """
    sensor_sizes: list[tuple[float, float]] = \
        get_sensors_size(ladder_id, conn)

    if not sensor_sizes:
        return 0.0, 0.0

    size_x = max(x for x, _ in sensor_sizes)


    raw_y = sum(y for _, y in sensor_sizes)
    if overlap_mm and len(sensor_sizes) > 1:
        raw_y -= overlap_mm * (len(sensor_sizes) - 1)
    size_y = raw_y

    return size_x, size_y

def list_ladder_names(conn, yaml : str|None = None) -> list[str]:
    sql = """
        SELECT name
        FROM public.sts_ladder
        ORDER BY name;
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        names = [r["name"] for r in cur.fetchall()]

    units = np.unique([int(n[1]) for n in names])
    unit_layout : dict[int, tuple[list[str], list[str]]] = {}
    for u in units:
        unit_layout[int(u)] = (16*[-1], 16*[-1])

    for n in names:
        unit = int(n[1])
        face = n[2]
        side = n[3]
        pos = int(n[4])
        if side == 'L':
            pos = 8 - pos
        else:
            pos = 8 + pos
        unit_layout[unit][0 if face == 'U' else 1][pos] = n

    for u in unit_layout.keys():
        print(f"Unit {u}:")
        print("  Upstream:   ", unit_layout[u][0])
        print("  Downstream: ", unit_layout[u][1])
    return names

if __name__ == "__main__":
    """
    Example usage when run as a script.

    - Takes an optional ladder ID as the first argument.
    - Prints modules and ladder size in Y.
    """
    ladder_id = sys.argv[1] if len(sys.argv) > 1 else "L4DL000161"

    try:
        conn = get_conn_from_env()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    try:
        # modules = get_ladder_modules(ladder_id, conn=conn, sorted=True)
        # print(f"Ladder: {ladder_id}")
        # print("Modules (top → bottom):")
        # for m in modules:
        #     print(f"  {m}")

        # size_y = compute_ladder_size_xy(ladder_id, conn=conn)[1]
        # print(f"\nTotal ladder size Y: {size_y:.1f} mm")

        # Uncomment for ad-hoc inspection:
        # print(list_tables(conn))
        # inspect_table(table_name="public.sts_module", limit=5, conn=conn)
        # inspect_table(table_name="public.sts_sensor_status", limit=5, conn=conn)
        # inspect_table(table_name="public.sts_ladder", limit=10, conn=conn)
        # print(get_module_sensor("M3DR6T0000150B2", conn=conn))

        ladder_names = list_ladder_names(conn)
        # print(len(ladder_names),"\n" ,ladder_names)
    finally:
        conn.close()
