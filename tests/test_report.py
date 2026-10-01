import json
from sparrow_capacity_planner.core import calculate
from sparrow_capacity_planner.fixtures import fixture_set
from sparrow_capacity_planner.report import render


def result():
    files = fixture_set()
    return calculate(files["capacity.json"], files["work.json"])


def test_report_matches_ground_truth_exact():
    actual = json.loads(render(result(), "json"))
    assert actual["totals"] == fixture_set()["expectations.json"]["totals"]
    markdown = render(result())
    for key, value in actual["totals"].items():
        assert f"| {key} | {value} |" in markdown


def test_report_zero_false_positives():
    actual = json.loads(render(result(), "json"))
    accepted = {r["id"] for r in actual["decisions"] if r["accepted"]}
    expected = set(fixture_set()["expectations.json"]["accepted_ids"])
    assert accepted == expected


def test_report_carries_provenance_banner():
    for format in ("md", "json"):
        assert "Data provenance:" in render(result(), format)
        assert "SYNTHETIC fixture" in render(result(), format)
    mixed = result()
    mixed["provenance"]["work"] = "henry_entered"
    assert "REAL input entered by Henry" in render(mixed)


def test_hypothetical_figures_labelled():
    for format in ("md", "json"):
        output = render(result(), format)
        assert "hypothetical" in output
        assert "not measured savings" in output


def test_no_em_dashes_in_outputs():
    for format in ("md", "json"):
        assert chr(0x2014) not in render(result(), format)
