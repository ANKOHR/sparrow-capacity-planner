# Sparrow Capacity Planner

A local Python CLI that computes how much proposed work fits into an explicitly entered capacity budget. Its decisions are hypothetical scenarios, not predictions. Intended for small business owners and Sparrow capacity audits.

Hypothesis: deterministic calculations against entered workload and capacity can provide an auditable basis for accepting work. The synthetic acceptance test establishes calculation correctness, not customer demand or real-world accuracy.

## Quickstart

Python 3.10 or later. No runtime dependencies, network calls, models, GPU workloads, or database server. Install from this directory using locally available setuptools:

```powershell
python -m pip install --no-index --no-deps --no-build-isolation -e .
scp fixtures --out demo
scp run --input demo
scp report --format md
python -m pytest -q
```

Alternatively use `python -m sparrow_capacity_planner.cli` in place of `scp`, without installing. pytest must already be available to run tests. Commands run sequentially in PowerShell; shells supporting `&&` can use the brief's one-line demo.

On Windows, add the Python user Scripts directory reported by pip to PATH and confirm `Get-Command scp` points to the installed Python entry point. Windows also supplies an unrelated OpenSSH program named scp. The module invocation above avoids that name collision. The capacity command prints totals without decision rows; accept prints the full allocation.

The smallest hand-written example is `examples/five`: run `scp run --input examples/five` then `scp report --format md`. Its hypothetical capacity is 240 minutes, commitments total 90, proposals C and E consume 150, and D is rejected. Zero minutes remain.

## Input format

Only UTF-8 JSON is supported. An input directory contains `capacity.json` and `work.json`. Optional `expectations.json` and `SYNTHETIC.md` are permitted and ignored by the engine. Other files produce a named schema error. No input is silently dropped. A genuinely empty directory produces an explicitly labelled no-input hypothetical zero report. A missing directory or one missing a required file produces an error with a usage hint.

`capacity.json`:

```json
{
  "synthetic": true,
  "source": "synthetic_fixture",
  "as_of": "2026-09-30",
  "window_start": "2026-10-01",
  "window_end": "2026-10-14",
  "available_minutes": 240
}
```

`work.json`:

```json
{
  "synthetic": true,
  "source": "synthetic_fixture",
  "records": [
    {"id": "A", "name": "Synthetic job", "status": "committed",
     "minutes": 60, "priority": 0, "recorded_on": "2026-09-30"}
  ]
}
```

Every documented field is required; unknown fields fail validation. All records apply to the entered planning window. The owner must enter net available minutes after leave, administration, and other unavailable time. The tool cannot infer these. For Henry's own manually entered real data, use `synthetic: false` and `source: "henry_entered"` independently in each input. These are self-declarations, not independently verified provenance. Mixed real and synthetic inputs are shown separately in the banner. Do not put other people's data under Henry's provenance label.

Minutes are integer units: capacity may be zero, job minutes must be positive, and both are limited to 1,000,000,000 per field. Booleans, fractions, negative values, NaN, and infinity fail validation. Priorities are integers 0 through 100; lower comes first. IDs must be unique. IDs and names allow Unicode and literal Windows paths, 1 through 10,000 characters, but no control characters or U+2014. JSON Windows paths require escaped backslashes. Dates must be YYYY-MM-DD. The window end cannot precede its start. Future planning windows are allowed; entry dates after explicit `as_of` are rejected. The program deliberately never consults today's clock, so reruns stay deterministic.

## Calculation rules and limits

1. Sum every committed job, regardless of priority.
2. Compute usable remaining capacity as max(0, available minus committed). Report any overbooked minutes separately.
3. Sort proposed jobs by ascending priority, then Unicode ID. Accept a whole job only if its entered minutes fit. Skip an oversized job and continue to smaller jobs. Never split jobs.
4. Report all proposed decisions, entered minute totals, counts, and remaining capacity.

This greedy policy is deterministic, but does not optimize revenue, job count, deadlines, skills, dependencies, or multiple resources. Zero free capacity rejects every positive proposed job. Committed work is never cancelled. Accepted plus rejected counts and minutes reconcile to proposed totals. Available plus overbooked minutes equals committed plus accepted plus remaining minutes. Neither uncertainty buffers nor inferred hours are added. The user chooses realistic inputs and buffers.

## Subcommand catalogue

Each command has `--help` with an example.

| Command | Example | Purpose |
| --- | --- | --- |
| fixtures | `scp fixtures --out demo` | Write 200 labelled synthetic jobs and hand-computed expectations |
| run | `scp run --input demo --results .scp/results.json` | Calculate, save, and print a hypothetical scenario |
| report | `scp report --format json --out report.json` | Render saved results with provenance; md is also supported |
| capacity | `scp capacity --input examples/five` | Inspect hypothetical capacity and commitments directly |
| accept | `scp accept --input demo` | Inspect hypothetical proposed work decisions directly |

`capacity` and `accept` calculate directly without saving results. `report` reads the snapshot saved by `run`; it does not reread current input. Rerun after editing input. Snapshots record SHA-256 of the exact input bytes and logical filenames. There are no timestamps, randomness, or absolute input paths in results. Identical inputs produce byte-identical results. No seed is necessary because generation uses fixed sequences.

## Architecture

```text
capacity.json + work.json
          |
     cli.py (read, validate errors, input hashes)
          |
     core.py (pure validation and hypothetical allocation)
          |
 .scp/results.json --> report.py --> Markdown / JSON

fixtures.py --> labelled synthetic files + independent expectations
```

## Honesty boundary and fixture labels

Every displayed scenario carries provenance and a hypothetical label, including minute totals and counts computed from entered assumptions. Real entered inputs do not make future allocation a measured outcome. The tool does not discover or predict work duration, recover time, or calculate savings. There are no time-saved or money-saved fields, since no measured baseline is supplied. Figures here are illustrative unless explicitly marked as a recorded local test observation.

Every synthetic JSON file contains `synthetic: true`; JSON forbids header comments, so the accompanying Markdown label includes an explicit synthetic header comment. The five-record example follows the same policy. The 200-record fixture has 100 commitments and 100 proposals, each 60 minutes. Hand arithmetic: 9,600 available minus 6,000 committed leaves 3,600, fitting 60 proposals; the other 40 require 2,400 minutes. `expectations.json` is independently specified and never read by the calculation. Tests compare all totals and complete accepted and rejected ID sets. Altering an input changes the calculations even if expectations are unchanged.

## Failure modes

Parse errors name the JSON file and line. Invalid UTF-8 is identified on line 1; duplicate-key errors name the key and its first occurrence line. Schema errors list offending fields and input filenames. Unsupported CSV and YAML receive a named unsupported-file error; they are not parsed. Missing inputs give a usage hint. All expected errors exit with code 2 without a traceback. CLI argument errors also exit 2. Successful commands exit 0.

Writes use a temporary UTF-8 file in the destination directory followed by atomic replacement. Write errors are named and remove the temporary file, preserving an existing destination. Fixture generation writes each file atomically; a failed multi-file generation can leave earlier complete files and should be rerun after correcting the path. Do not place output reports in the input directory. Existing fixture files and result snapshots at the specified destination are replaced on rerun.

## Evidence and improvement hook

See `EVIDENCE.md` for measured local validation. No real use or time savings have been measured. Henry can enter his own data by hand and retain trial results outside the shipped repository. Start the two-week window on the first real trial, not the build date.

Measure allocation agreement on a hand-checked sample: disagreement rate = proposed decisions differing from a manual application of the documented policy / sampled proposed decisions. Record the sample size, input hashes, mismatched IDs, active use days, and any measured run time separately. If disagreement exceeds 10 percent, fix the top cause and rerun the sample; if there is no actual use, record that finding and kill the project. Zero sampled decisions means accuracy is unmeasured, not zero error. Do not infer productivity savings from execution speed.

After two weeks, record an explicit verdict and reason in `VERDICT.md`: expand for daily use or revenue; integrate for substantial sibling overlap; commercialise for a willing buyer; maintain for portfolio evidence otherwise; kill for no use or unmet acceptance criteria. The current provisional verdict is maintain, awaiting the real evidence window. The final two-week verdict cannot honestly be supplied at build time.
