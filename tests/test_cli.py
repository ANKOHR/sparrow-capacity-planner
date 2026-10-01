import json
import subprocess
import sys
import time
from pathlib import Path
import pytest
from sparrow_capacity_planner.cli import main, load, atomic_write, InputError
from sparrow_capacity_planner.fixtures import generate


@pytest.fixture
def fixture(tmp_path):
    directory = tmp_path / "input"
    generate(directory, atomic_write)
    return directory


def test_run_completes_on_fixture(fixture, tmp_path, capsys):
    start = time.perf_counter()
    results = tmp_path / "results.json"
    assert main(["run", "--input", str(fixture), "--results", str(results)]) == 0
    assert main(["report", "--results", str(results), "--format", "md"]) == 0
    assert time.perf_counter() - start < 5
    assert "Data provenance:" in capsys.readouterr().out


def test_empty_input_renders_without_traceback(tmp_path, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    results = tmp_path / "result.json"
    assert main(["run", "--input", str(empty), "--results", str(results)]) == 0
    assert main(["report", "--results", str(results)]) == 0
    output = capsys.readouterr().out
    assert "NO INPUT" in output
    assert all(v == 0 for v in json.loads(results.read_text())["totals"].values())


def test_malformed_input_named_error(fixture, capsys):
    (fixture / "work.json").write_text('{\n  "records": bad\n}', encoding="utf-8")
    assert main(["capacity", "--input", str(fixture)]) == 2
    error = capsys.readouterr().err
    assert "ParseError" in error and "work.json" in error and "line 2" in error
    assert "Traceback" not in error


def test_determinism_byte_identical(fixture, tmp_path, capsys):
    results = tmp_path / "results.json"
    argv = ["run", "--input", str(fixture), "--results", str(results)]
    main(argv)
    first = (results.read_bytes(), capsys.readouterr().out)
    main(argv)
    assert first == (results.read_bytes(), capsys.readouterr().out)
    outputs = []
    for _ in range(2):
        main(["report", "--results", str(results)])
        outputs.append(capsys.readouterr().out)
    assert outputs[0] == outputs[1]


def test_cli_smoke_all_subcommands(fixture, tmp_path, capsys):
    assert main(["fixtures", "--out", str(tmp_path / "new")]) == 0
    for command in ("capacity", "accept"):
        assert main([command, "--input", str(fixture)]) == 0
    for command in ("fixtures", "run", "report", "capacity", "accept"):
        with pytest.raises(SystemExit) as exit_info:
            main([command, "--help"])
        assert exit_info.value.code == 0
        assert "Example:" in capsys.readouterr().out


def test_missing_input_and_write_failure(tmp_path, capsys):
    assert main(["capacity", "--input", str(tmp_path / "missing")]) == 2
    assert "Use scp fixtures" in capsys.readouterr().err
    blocker = tmp_path / "blocker"
    blocker.write_text("unchanged")
    with pytest.raises(InputError, match="WriteError"):
        atomic_write(blocker / "result.json", "data")
    assert blocker.read_text() == "unchanged"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["blocker"]


def test_duplicate_json_keys(fixture, capsys):
    (fixture / "work.json").write_text('{"records": [], "records": []}')
    assert main(["accept", "--input", str(fixture)]) == 2
    assert "duplicate JSON key" in capsys.readouterr().err


def test_expectations_are_not_used(fixture):
    (fixture / "expectations.json").write_text('{"wrong": true}')
    assert load(fixture)["totals"]["accepted_count"] == 60


def test_subprocess_entrypoint(fixture):
    completed = subprocess.run([sys.executable, "-m", "sparrow_capacity_planner.cli", "capacity", "--input", str(fixture)], capture_output=True, encoding="utf-8")
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["totals"]["accepted_count"] == 60


@pytest.mark.parametrize("mutation", ["provenance", "totals", "structure"])
def test_invalid_saved_report_named_error(fixture, tmp_path, capsys, mutation):
    result = load(fixture)
    if mutation == "provenance":
        result["provenance"]["work"] = "unknown"
    elif mutation == "totals":
        result["totals"]["accepted_count"] = 999
    else:
        result["decisions"] = [None]
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    assert main(["report", "--results", str(path)]) == 2
    error = capsys.readouterr().err
    assert "SchemaError" in error and str(path) in error
    assert "Traceback" not in error


def test_domain_commands_have_distinct_outputs(fixture, capsys):
    assert main(["capacity", "--input", str(fixture)]) == 0
    capacity = json.loads(capsys.readouterr().out)
    assert "decisions" not in capacity
    assert main(["accept", "--input", str(fixture)]) == 0
    accept = json.loads(capsys.readouterr().out)
    assert len(accept["decisions"]) == 100
    assert capacity["totals"] == accept["totals"]


def test_report_write_failure_leaves_no_partial_files(fixture, tmp_path, capsys):
    result = tmp_path / "results.json"
    assert main(["run", "--input", str(fixture), "--results", str(result)]) == 0
    destination = tmp_path / "destination"
    destination.mkdir()
    assert main(["report", "--results", str(result), "--out", str(destination)]) == 2
    assert "WriteError" in capsys.readouterr().err
    assert list(destination.iterdir()) == []
    assert sorted(p.name for p in tmp_path.iterdir()) == ["destination", "input", "results.json"]
