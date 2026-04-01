UNIT_FACE = ["D", "U"]
UNIT_SIDE = ["R", "L"]

def is_valid_ladder_name(name: str) -> bool:
    return (
        len(name) == 10
        and name[0].upper() == "L"
        and name[1].isdigit()
        and name[2] in UNIT_FACE
        and name[3] in UNIT_SIDE
        and name[4:].isnumeric()
    )
