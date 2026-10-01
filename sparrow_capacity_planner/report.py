"""Deterministic reports with visible provenance and hypothetical labels."""
import json
from .core import fields, require, integer


def validate_result(result):
    """Reject malformed snapshots rather than inventing provenance or figures."""
    require(isinstance(result, dict), "result", "must be an object")
    for key in ("schema_version", "figure_status", "provenance", "window", "totals", "decisions"):
        require(key in result, key, "missing saved result field")
    require(result["schema_version"] == 1, "schema_version", "must be 1")
    require(isinstance(result["figure_status"], str) and "hypothetical" in result["figure_status"], "figure_status", "must label the scenario hypothetical")
    fields(result["provenance"], {"capacity", "work"}, "provenance")
    for key, source in result["provenance"].items():
        require(source in ("synthetic_fixture", "henry_entered", "no_input"), "provenance." + key, "unknown source")
    fields(result["window"], {"as_of", "window_start", "window_end"}, "window")
    require(all(isinstance(value, str) for value in result["window"].values()), "window", "values must be strings")
    keys = {"record_count", "available_minutes", "committed_count", "committed_minutes", "proposed_count", "proposed_minutes", "accepted_count", "accepted_minutes", "rejected_count", "rejected_minutes", "remaining_minutes", "overbooked_minutes"}
    fields(result["totals"], keys, "totals")
    totals = result["totals"]
    for key, value in totals.items():
        integer(value, "totals." + key, maximum=10**30)
    require(isinstance(result["decisions"], list), "decisions", "must be a list")
    ids = set()
    for row in result["decisions"]:
        fields(row, {"id", "minutes", "accepted", "reason"}, "decisions")
        require(isinstance(row["id"], str), "decisions.id", "must be a string")
        require(row["id"] not in ids, "decisions.id", "duplicate id")
        ids.add(row["id"])
        integer(row["minutes"], "decisions.minutes")
        require(row["minutes"] > 0, "decisions.minutes", "must be positive")
        require(type(row["accepted"]) is bool, "decisions.accepted", "must be boolean")
        require(row["reason"] == ("fits_entered_capacity" if row["accepted"] else "insufficient_entered_capacity"), "decisions.reason", "must match decision")
    for accepted, prefix in ((True, "accepted"), (False, "rejected")):
        rows = [row for row in result["decisions"] if row["accepted"] == accepted]
        require(totals[prefix + "_count"] == len(rows) and totals[prefix + "_minutes"] == sum(row["minutes"] for row in rows), "totals." + prefix, "must reconcile with decisions")
    require(totals["proposed_count"] == len(result["decisions"]) and totals["proposed_minutes"] == totals["accepted_minutes"] + totals["rejected_minutes"], "totals.proposed", "must reconcile")
    require(totals["record_count"] == totals["committed_count"] + totals["proposed_count"], "totals.record_count", "must reconcile")
    require(totals["overbooked_minutes"] == max(0, totals["committed_minutes"] - totals["available_minutes"]), "totals.overbooked_minutes", "must reconcile")
    require(totals["available_minutes"] + totals["overbooked_minutes"] == totals["committed_minutes"] + totals["accepted_minutes"] + totals["remaining_minutes"], "totals.remaining_minutes", "must reconcile")
    require(chr(0x2014) not in json_text(result), "result", "U+2014 is forbidden")


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def banner(result):
    sources = result["provenance"]
    return "Data provenance: " + "; ".join(f"{key} = {'SYNTHETIC fixture' if value == 'synthetic_fixture' else ('NO INPUT, hypothetical zero scenario' if value == 'no_input' else 'REAL input entered by Henry (self-declared, not verified)')}" for key, value in sorted(sources.items()))


def render(result, format="md"):
    validate_result(result)
    if format == "json":
        return json_text({**result, "provenance_banner": banner(result)})
    lines = ["# Sparrow Capacity Planner", "", banner(result), "", "Figure status: " + result["figure_status"], "",
             "Planning window: " + result["window"]["window_start"] + " to " + result["window"]["window_end"], "",
             "All minute totals and job counts below describe the hypothetical scenario.", "", "| Figure | Value |", "| --- | ---: |"]
    lines.extend(f"| {key} | {value} |" for key, value in sorted(result["totals"].items()))
    lines.extend(["", "## Proposed work decisions", "", "| ID | Entered minutes | Scenario decision | Reason |", "| --- | ---: | --- | --- |"])
    for row in result["decisions"]:
        identifier = row["id"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;")
        lines.append(f"| {identifier} | {row['minutes']} | {'accept' if row['accepted'] else 'reject'} | {row['reason']} |")
    return "\n".join(lines) + "\n"
