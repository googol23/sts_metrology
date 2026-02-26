from typing import Any, Dict, List
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import yaml

# ------------------------------------------------------------------
# DB connection
# ------------------------------------------------------------------

def get_conn_from_env() -> psycopg2.extensions.connection:
    """Get a DB connection, raise error if fails."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "pgsql.gsi.de"),
            port=os.getenv("DB_PORT", "8646"),
            dbname=os.getenv("DB_NAME", "dtl"),
            user=os.getenv("DB_USER", "dtl_read"),
            password=os.getenv("DB_PASSWORD", "SFVZkz3FsuDRBfpZ5OVc"),
            cursor_factory=RealDictCursor,
            connect_timeout=10,
        )
        return conn
    except Exception as e:
        raise RuntimeError(f"Failed to connect to DB: {e}")

# ------------------------------------------------------------------
# Queries
# ------------------------------------------------------------------

def list_ladder_names(conn) -> List[str]:
    sql = "SELECT name FROM public.sts_ladder ORDER BY name;"
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    if not rows:
        raise ValueError("No ladder names found in DB.")
    return [r["name"] for r in rows]

def get_latest_modules_for_ladder(ladder_name: str, conn) -> List[str]:
    """
    Keep only the latest version of each module.
    Version is the 8th character in the name.
    """
    sql = """
        SELECT
            MAX(substring(name, 8, 1)) AS version,
            overlay(name, '0', 8, 1) AS name_base
        FROM public.sts_module
        WHERE ladder_name = %s
        GROUP BY name_base;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (ladder_name,))
        rows = cur.fetchall()
    if not rows:
        raise ValueError(f"No modules found for ladder {ladder_name}.")

    modules: List[str] = []
    for r in rows:
        base = r["name_base"]
        version = r["version"]
        if not base or not version:
            raise ValueError(f"Invalid module data: {r}")
        if len(base) < 8:
            raise ValueError(f"Module name too short: {base}")
        modules.append(base[:7] + version + base[8:])

    return modules

# ------------------------------------------------------------------
# Assembly logic
# ------------------------------------------------------------------

def build_ladder_layout(conn) -> Dict[str, List[str]]:
    layout: Dict[str, List[str]] = {}

    sql_sensor = """
        SELECT get_sensor_size_mm(sensor_name::smallint) AS size
        FROM public.sts_module
        WHERE name = %s;
    """

    for ladder in list_ladder_names(conn):
        modules = get_latest_modules_for_ladder(ladder, conn)

        if len(modules) % 2 != 0:
            raise ValueError(f"Ladder {ladder} module list is not symmetric")

        sensor_sizes: List[str] = []

        with conn.cursor() as cur:
            for m in modules:
                if len(m) < 6:
                    raise ValueError(f"Invalid module name length: {m}")
                # keep only TOP modules
                if m[5] != "T":
                    continue

                cur.execute(sql_sensor, (m,))
                row = cur.fetchone()
                if not row or not row["size"]:
                    raise ValueError(f"Missing sensor size for module {m}")
                sensor_sizes.append("k" + row["size"].replace("x", "_"))

        layout[patch_ladder_name(ladder)] = sensor_sizes

    return layout

# ------------------------------------------------------------------
# Patch ladder names after STS3+5
# ------------------------------------------------------------------

def patch_ladder_name(ladder_name: str) -> str:
    if len(ladder_name) < 3:
        raise ValueError(f"Invalid ladder name: {ladder_name}")

    unit_index = int(ladder_name[1])
    unit_face = ladder_name[2]

    if (unit_index == 3 and unit_face == "D") or unit_index > 3:
        new_index = unit_index + 1
        return ladder_name[0] + str(new_index) + ladder_name[2:]
    return ladder_name

# ------------------------------------------------------------------
# Rules
# ------------------------------------------------------------------

def check_ladder_names(yaml_data) -> bool:
    for entry in yaml_data.get("types", []):
        name = list(entry.keys())[0]
        if name.startswith("L3D") or name.startswith("L4U"):
            raise ValueError(
                f"Invalid ladder name: {name}. Old unit 3 was broken down into 3U and 4D."
            )
    return True

# ------------------------------------------------------------------
# YAML dumping
# ------------------------------------------------------------------

class FlowList(list):
    """Marker type for flow-style lists."""

def flow_list_representer(dumper, data):
    return dumper.represent_sequence(
        "tag:yaml.org,2002:seq",
        data,
        flow_style=True,
    )

yaml.add_representer(FlowList, flow_list_representer)

def dump_ladders_to_yaml(layout: dict[str, list[str]], filename: str) -> dict:
    if not layout:
        raise ValueError("Layout is empty, aborting YAML generation.")

    yaml_data = {
        "types": [
            {
                ladder: {
                    "length": 10,
                    "firstSensorOffsetY": 20,
                    "layout": FlowList(sizes),
                }
            }
            for ladder, sizes in layout.items()
        ]
    }

    yaml_data["types"].sort(key=lambda d: list(d.keys())[0])
    check_ladder_names(yaml_data)

    with open(filename, "w") as f:
        yaml.dump(yaml_data, f, sort_keys=False, default_flow_style=False)

    print("layout.yml written successfully")
    return yaml_data

# ------------------------------------------------------------------
# Generate unit layout
# ------------------------------------------------------------------

def generate_unit_layout(yaml_data) ->  dict[int, dict[str, list[str]]]:
    layout: dict[int, dict[str, list[str]]] = {}

    for entry in yaml_data["types"]:
        name = list(entry.keys())[0]
        unit_index = int(name[1])
        unit_face = "upstream" if name[2] == "U" else "downstream"
        unit_side = name[3]
        slot = 8 + int(name[4]) if unit_side == "L" else 7 - int(name[4])

        if not 0 <= slot < 16:
            raise ValueError(f"Calculated slot {slot} for {name} is out of bounds")

        if unit_index not in layout:
            layout[unit_index] = {
                "upstream": ["kNone"] * 16,
                "downstream": ["kNone"] * 16
            }

        layout[unit_index][unit_face][slot] = name

    width = 12
    sep = "|"
    for unit, faces in layout.items():
        for slot, elem in enumerate(faces["upstream"]):
            print(f"{elem:<{width}}", end="")
            if slot == 7:
                print(f"{sep:<{3}}", end="")
        print()
        for slot, elem in enumerate(faces["downstream"]):
            print(f"{elem:<{width}}", end="")
            if slot == 7:
                print(f"{sep:<{3}}", end="")
        print()

def dump_units_to_yaml(layout: dict[int, dict[str, list[str]]], filename: str) -> dict:
    """
    Dump the per-unit layout dictionary to a YAML file.

    Args:
        layout: Dictionary of the form
                {unit_index: {"upstream": [...], "downstream": [...]}}
        filename: Output YAML filename.

    Returns:
        The YAML dictionary that was written.
    """
    if not layout:
        raise ValueError("Unit layout is empty, cannot dump YAML.")

    yaml_data = {"units": []}

    for unit_index, faces in layout.items():
        if "upstream" not in faces or "downstream" not in faces:
            raise ValueError(f"Unit {unit_index} missing 'upstream' or 'downstream' face data.")

        if len(faces["upstream"]) != 16 or len(faces["downstream"]) != 16:
            raise ValueError(f"Unit {unit_index} upstream/downstream lists must have length 16.")

        unit_entry = {
            "unit_index": unit_index,
            "upstream": FlowList(faces["upstream"]),
            "downstream": FlowList(faces["downstream"]),
        }
        yaml_data["units"].append(unit_entry)

    # Sort units by unit_index
    yaml_data["units"].sort(key=lambda u: u["unit_index"])

    # Write to file
    with open(filename, "w") as f:
        yaml.dump(yaml_data, f, sort_keys=False, default_flow_style=False)

    print(f"{filename} written successfully with {len(yaml_data['units'])} units.")
    return yaml_data


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    conn = get_conn_from_env()
    try:
        layout = build_ladder_layout(conn)
        yaml_dict = dump_ladders_to_yaml(layout, "layout.yml")
        generate_unit_layout(yaml_dict)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
