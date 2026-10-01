# Recorded local build evidence

Measured on 2026-10-01 using Python 3.12 on Windows, CPU only.

- pytest: 37 passed in 0.66 seconds.
- Installed Python scp entry point, fixtures + run + Markdown report: 0.746055 seconds, below 5 seconds.
- Separate installed scp JSON report: 0.225003 seconds, below 5 seconds.
- All 12 reported totals match the independently specified 200-record ground truth exactly.
- Accepted IDs: job-100 through job-159, all 60 found; rejected IDs: job-160 through job-199, all 40 found. Zero false positives.
- Hand-written five-record example: 90 committed minutes, 150 accepted minutes, zero remaining.
- Mutating committed input from 60 to 120 minutes changes accepted count from 60 to 59, independently of expectations.json.
- Deterministic reruns, malformed input, schema drift, duplicate IDs, future entry dates, negative and extreme values, Unicode, long strings, empty input, saved-report validation and atomic write failures pass tests.

These are measured local software checks on synthetic inputs, not measured customer savings or real-use accuracy. No real trial has started. No network calls or publishing were performed. No randomness or seed is used.

Evidence-based improvement: saved reports previously treated unknown provenance as real. Validation now rejects unknown provenance and inconsistent totals, pinned by regression tests. This closes a concrete honesty failure found during code review.
