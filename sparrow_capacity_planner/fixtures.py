"""Synthetic fixtures with independently specified hand-computed expectations.
No randomness is used, so no random seed is needed.
"""
from .report import json_text


def fixture_set():
    config = {"synthetic": True, "source": "synthetic_fixture", "as_of": "2026-09-30",
              "window_start": "2026-10-01", "window_end": "2026-10-14", "available_minutes": 9600}
    records = [{"id": f"job-{i:03}", "name": f"Synthetic job {i}",
                "status": "committed" if i < 100 else "proposed", "minutes": 60,
                "priority": 0, "recorded_on": "2026-09-30"} for i in range(200)]
    expected = {"synthetic": True, "label": "SYNTHETIC hand-computed ground truth",
                "arithmetic": "100*60=6000 committed; 9600-6000=3600; 3600/60=60 accepted; 40*60=2400 rejected",
                "totals": {"record_count": 200, "available_minutes": 9600, "committed_count": 100,
                           "committed_minutes": 6000, "proposed_count": 100, "proposed_minutes": 6000,
                           "accepted_count": 60, "accepted_minutes": 3600, "rejected_count": 40,
                           "rejected_minutes": 2400, "remaining_minutes": 0, "overbooked_minutes": 0},
                "accepted_ids": [f"job-{i:03}" for i in range(100, 160)],
                "rejected_ids": [f"job-{i:03}" for i in range(160, 200)]}
    return {"capacity.json": config, "work.json": {"synthetic": True, "source": "synthetic_fixture", "records": records}, "expectations.json": expected}


def generate(directory, write):
    for name, value in fixture_set().items():
        write(directory / name, json_text(value))
    write(directory / "SYNTHETIC.md", "<!-- SYNTHETIC fixture set -->\n# SYNTHETIC fixtures\nEvery JSON file has synthetic: true. JSON does not permit header comments.\n")
