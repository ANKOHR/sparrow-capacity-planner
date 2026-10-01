"""Local-only command line interface for hypothetical capacity scenarios."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from .core import SchemaError, calculate
from .fixtures import generate
from .report import json_text, render


class InputError(ValueError):
    pass


def atomic_write(path, text):
    temporary = None
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        os.replace(temporary, path)
    except OSError as exc:
        raise InputError(f"WriteError: {path}: {exc.strerror}") from exc
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def read_json(path):
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        def no_duplicates(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise InputError(f"ParseError: {path}: line {text[:text.find(json.dumps(key))].count(chr(10)) + 1}: duplicate JSON key {key}")
                result[key] = value
            return result
        return json.loads(text, object_pairs_hook=no_duplicates), hashlib.sha256(raw).hexdigest()
    except json.JSONDecodeError as exc:
        raise InputError(f"ParseError: {path}: line {exc.lineno}: {exc.msg}") from exc
    except UnicodeDecodeError as exc:
        raise InputError(f"ParseError: {path}: line 1: input must be UTF-8") from exc
    except OSError as exc:
        raise InputError(f"InputError: {path}: {exc.strerror}. Use scp fixtures --out demo or provide capacity.json and work.json") from exc


def load(directory):
    if not directory.is_dir():
        raise InputError(f"InputError: {directory}: missing input directory. Use scp fixtures --out demo")
    contents = sorted(p.name for p in directory.iterdir())
    if not contents:
        return {"schema_version": 1, "figure_status": "hypothetical empty-input scenario; no measured savings or forecast",
                "provenance": {"capacity": "no_input", "work": "no_input"},
                "window": {"as_of": "unspecified", "window_start": "unspecified", "window_end": "unspecified"},
                "totals": {key: 0 for key in ("record_count", "available_minutes", "committed_count", "committed_minutes", "proposed_count", "proposed_minutes", "accepted_count", "accepted_minutes", "rejected_count", "rejected_minutes", "remaining_minutes", "overbooked_minutes")}, "decisions": [], "inputs": [], "empty_input": True}
    unknown = set(contents) - {"capacity.json", "work.json", "expectations.json", "SYNTHETIC.md"}
    if unknown:
        raise InputError(f"SchemaError: {directory}: unsupported input file(s): {', '.join(sorted(unknown))}. Only documented JSON files are accepted")
    config, chash = read_json(directory / "capacity.json")
    data, dhash = read_json(directory / "work.json")
    try:
        result = calculate(config, data)
    except SchemaError as exc:
        raise InputError(f"{exc}; files: {directory / 'capacity.json'}, {directory / 'work.json'}") from exc
    result["inputs"] = [{"file": "capacity.json", "sha256": chash}, {"file": "work.json", "sha256": dhash}]
    return result


def parser():
    root = argparse.ArgumentParser(prog="scp", description="Compute hypothetical work capacity from explicit local inputs. No forecasts or measured savings.")
    commands = root.add_subparsers(dest="command", required=True)
    fixture = commands.add_parser("fixtures", help="Generate 200 labelled synthetic jobs", epilog="Example: scp fixtures --out demo")
    fixture.add_argument("--out", type=Path, required=True)
    run = commands.add_parser("run", help="Compute and save a hypothetical capacity scenario", epilog="Example: scp run --input demo")
    run.add_argument("--input", type=Path, required=True)
    run.add_argument("--results", type=Path, default=Path(".scp/results.json"))
    report = commands.add_parser("report", help="Render the saved scenario with provenance", epilog="Example: scp report --format md")
    report.add_argument("--format", choices=("md", "json"), default="md")
    report.add_argument("--results", type=Path, default=Path(".scp/results.json"))
    report.add_argument("--out", type=Path)
    for name, help_text in (("capacity", "Show entered capacity, commitments and remaining minutes"), ("accept", "Show hypothetical accept/reject decisions in priority order")):
        command = commands.add_parser(name, help=help_text, description=help_text + ". All figures are hypothetical.", epilog=f"Example: scp {name} --input demo")
        command.add_argument("--input", type=Path, required=True)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "fixtures":
            generate(args.out, atomic_write)
            print("Generated SYNTHETIC fixtures: 200 jobs, hypothetical inputs.")
        elif args.command == "run":
            result = load(args.input)
            atomic_write(args.results, json_text(result))
            print(render(result, "json"), end="")
        elif args.command == "report":
            result, _ = read_json(args.results)
            try:
                output = render(result, args.format)
            except (KeyError, TypeError, AttributeError, SchemaError) as exc:
                raise InputError(f"SchemaError: {args.results}: invalid saved result field: {exc}") from exc
            if args.out:
                atomic_write(args.out, output)
            else:
                print(output, end="")
        else:
            scenario = json.loads(render(load(args.input), "json"))
            if args.command == "capacity":
                scenario.pop("decisions")
            print(json_text(scenario), end="")
        return 0
    except (InputError, SchemaError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
