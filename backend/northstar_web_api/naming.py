"""
Postgres columns are snake_case (idiomatic SQL); every page in
frontend/northstar_web/ already expects camelCase JSON (shipperId, pickupDate,
...) from its old localStorage days. These two helpers translate at the
API boundary so no JS on any of the 22 pages needs to change field names.
"""
# ------------------------------------------
# SNAKE -> CAMEL — one dict, top-level keys only (rows are always flat)
# ------------------------------------------
def to_camel(snake: str) -> str:
    head, *tail = snake.split("_")
    return head + "".join(word.capitalize() for word in tail)


def row_to_camel(row: dict) -> dict:
    return {to_camel(k): v for k, v in row.items()}


# ------------------------------------------
# CAMEL -> SNAKE — for turning a request body back into column names
# ------------------------------------------
def to_snake(camel: str) -> str:
    out = []
    for ch in camel:
        if ch.isupper():
            out.append("_")
            out.append(ch.lower())
        else:
            out.append(ch)
    return "".join(out)


def payload_to_snake(payload: dict) -> dict:
    return {to_snake(k): v for k, v in payload.items()}
