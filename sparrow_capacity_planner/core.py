"""Pure calculations for hypothetical capacity scenarios using entered minutes."""
from datetime import date


class SchemaError(ValueError):
    """An explicit input field violates the documented schema."""


def require(condition, field, message):
    if not condition:
        raise SchemaError(f"SchemaError: {field}: {message}")


def integer(value, field, maximum=10**9):
    require(type(value) is int and 0 <= value <= maximum, field,
            f"must be an integer between 0 and {maximum}")


def fields(value, expected, field):
    require(isinstance(value, dict), field, "must be an object")
    require(set(value) == set(expected), field,
            f"required fields {sorted(expected)}; missing {sorted(set(expected)-set(value))}; unknown {sorted(set(value)-set(expected))}")


def validate(config, data):
    fields(config, {"synthetic", "source", "as_of", "window_start", "window_end", "available_minutes"}, "capacity")
    fields(data, {"synthetic", "source", "records"}, "work")
    for name, obj in (("capacity", config), ("work", data)):
        require(type(obj["synthetic"]) is bool, name + ".synthetic", "must be boolean")
        require(obj["source"] in ("synthetic_fixture", "henry_entered"), name + ".source", "must be synthetic_fixture or henry_entered")
        require(obj["synthetic"] == (obj["source"] == "synthetic_fixture"), name + ".source", "must agree with synthetic flag")
    dates = {}
    for field in ("as_of", "window_start", "window_end"):
        try:
            require(isinstance(config[field], str), field, "must be ISO date")
            dates[field] = date.fromisoformat(config[field])
            require(dates[field].isoformat() == config[field], field, "must be YYYY-MM-DD")
        except (ValueError, TypeError) as exc:
            raise SchemaError(f"SchemaError: capacity.{field}: must be YYYY-MM-DD") from exc
    require(dates["window_start"] <= dates["window_end"], "window_end", "must not precede window_start")
    integer(config["available_minutes"], "available_minutes")
    require(isinstance(data["records"], list), "records", "must be a list")
    ids = set()
    for i, row in enumerate(data["records"]):
        prefix = f"records[{i}]"
        fields(row, {"id", "name", "status", "minutes", "priority", "recorded_on"}, prefix)
        for key in ("id", "name"):
            require(isinstance(row[key], str) and 0 < len(row[key]) <= 10000, prefix + "." + key, "must contain 1 to 10000 characters")
            require(not any(ord(c) < 32 for c in row[key]) and chr(0x2014) not in row[key], prefix + "." + key, "control characters and U+2014 are forbidden")
        require(row["id"] not in ids, prefix + ".id", "duplicate id")
        ids.add(row["id"])
        require(row["status"] in ("committed", "proposed"), prefix + ".status", "must be committed or proposed")
        integer(row["minutes"], prefix + ".minutes")
        require(row["minutes"] > 0, prefix + ".minutes", "must be positive")
        integer(row["priority"], prefix + ".priority", 100)
        try:
            recorded = date.fromisoformat(row["recorded_on"])
            require(recorded.isoformat() == row["recorded_on"], prefix + ".recorded_on", "must be YYYY-MM-DD")
        except (ValueError, TypeError) as exc:
            raise SchemaError(f"SchemaError: {prefix}.recorded_on: must be YYYY-MM-DD") from exc
        require(recorded <= dates["as_of"], prefix + ".recorded_on", "future entry relative to as_of")


def calculate(config, data):
    """Compute a hypothetical greedy scenario, not a forecast or optimum."""
    validate(config, data)
    committed = [r for r in data["records"] if r["status"] == "committed"]
    proposed = sorted((r for r in data["records"] if r["status"] == "proposed"), key=lambda r: (r["priority"], r["id"]))
    used = sum(r["minutes"] for r in committed)
    remaining = max(0, config["available_minutes"] - used)
    decisions = []
    for row in proposed:
        fits = row["minutes"] <= remaining
        if fits:
            remaining -= row["minutes"]
        decisions.append({"id": row["id"], "minutes": row["minutes"], "accepted": fits,
                          "reason": "fits_entered_capacity" if fits else "insufficient_entered_capacity"})
    accepted = [r for r in decisions if r["accepted"]]
    totals = {"record_count": len(data["records"]), "available_minutes": config["available_minutes"],
              "committed_count": len(committed), "committed_minutes": used,
              "proposed_count": len(proposed), "proposed_minutes": sum(r["minutes"] for r in proposed),
              "accepted_count": len(accepted), "accepted_minutes": sum(r["minutes"] for r in accepted),
              "rejected_count": len(decisions)-len(accepted),
              "rejected_minutes": sum(r["minutes"] for r in decisions if not r["accepted"]),
              "remaining_minutes": remaining, "overbooked_minutes": max(0, used-config["available_minutes"])}
    return {"schema_version": 1, "figure_status": "hypothetical scenario computed from entered inputs; not measured savings or a forecast",
            "provenance": {"capacity": config["source"], "work": data["source"]},
            "window": {k: config[k] for k in ("as_of", "window_start", "window_end")},
            "totals": totals, "decisions": decisions}
