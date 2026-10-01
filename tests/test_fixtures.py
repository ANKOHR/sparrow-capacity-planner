import json
from sparrow_capacity_planner.fixtures import fixture_set, generate
from sparrow_capacity_planner.cli import atomic_write
from sparrow_capacity_planner.core import calculate


def test_fixtures_labelled_synthetic(tmp_path):
    generate(tmp_path, atomic_write)
    for path in tmp_path.glob("*.json"):
        assert json.loads(path.read_text(encoding="utf-8"))["synthetic"] is True
    assert "<!-- SYNTHETIC" in (tmp_path / "SYNTHETIC.md").read_text()


def test_fixture_ground_truth_matches_hand_computed():
    files = fixture_set()
    expected = files["expectations.json"]
    result = calculate(files["capacity.json"], files["work.json"])
    assert len(files["work.json"]["records"]) == 200
    assert result["totals"] == expected["totals"]
    assert [r["id"] for r in result["decisions"] if r["accepted"]] == expected["accepted_ids"]
    assert [r["id"] for r in result["decisions"] if not r["accepted"]] == expected["rejected_ids"]
