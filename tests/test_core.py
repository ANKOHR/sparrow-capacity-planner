import copy
import pytest
from sparrow_capacity_planner.core import calculate, SchemaError
from sparrow_capacity_planner.fixtures import fixture_set


def inputs():
    fixture = fixture_set()
    return fixture["capacity.json"], fixture["work.json"]


@pytest.mark.parametrize("field,value", [("minutes", -1), ("minutes", True), ("minutes", 1.5), ("minutes", float("nan")), ("minutes", 10**10), ("priority", -1), ("recorded_on", "2026-10-01"), ("recorded_on", "bad"), ("name", "x"*10001), ("name", "bad\nname"), ("name", "bad"+chr(0x2014))])
def test_rejects_adversarial_values(field, value):
    config, data = inputs()
    data["records"][0][field] = value
    with pytest.raises(SchemaError, match=field):
        calculate(config, data)


def test_duplicate_ids_and_schema_drift():
    config, data = inputs()
    data["records"][1]["id"] = data["records"][0]["id"]
    with pytest.raises(SchemaError, match="duplicate id"):
        calculate(config, data)
    config, data = inputs()
    data["records"][0]["extra"] = 1
    with pytest.raises(SchemaError, match="extra"):
        calculate(config, data)


def test_handles_unicode_and_long_inputs():
    config, data = inputs()
    data["records"][100]["id"] = "客户 café C:\\work\\job"
    data["records"][100]["name"] = "客" * 10000
    result = calculate(config, data)
    assert any(d["id"] == data["records"][100]["id"] for d in result["decisions"])


def test_corrupted_fixture_changes_computed_results():
    config, data = inputs()
    before = calculate(config, data)
    data["records"][0]["minutes"] = 120
    after = calculate(config, data)
    assert after["totals"]["accepted_count"] == 59
    assert before["totals"] != after["totals"]


def test_overbooked_and_greedy_skip():
    config, data = inputs()
    config["available_minutes"] = 0
    assert calculate(config, data)["totals"]["overbooked_minutes"] == 6000
    config["available_minutes"] = 6070
    data["records"][100]["minutes"] = 80
    result = calculate(config, data)
    assert not result["decisions"][0]["accepted"]
    assert result["decisions"][1]["accepted"]
    assert result["totals"]["remaining_minutes"] == 10


def test_calculation_does_not_mutate_inputs():
    config, data = inputs()
    before = copy.deepcopy((config, data))
    calculate(config, data)
    assert (config, data) == before
