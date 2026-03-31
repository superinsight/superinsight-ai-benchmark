#!/usr/bin/env python3
"""
Patch existing golden.json files to add may_extract entries.

Scans each synthetic source for clinical encounter-like segments that are NOT
in the golden entries, and adds them as may_extract. This fixes the false
positive problem where LLM-synthesized sources contain extra clinical encounters.

Usage:
    python patch_golden_may_extract.py
    python patch_golden_may_extract.py --dry-run
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).parent.parent))
from synthesize_golden import _scan_for_extra_encounters, _extract_noise_dates


GOLDEN_DIRS = ["golden/golden_a", "golden/golden_b", "golden/golden_c"]


def patch_golden(golden_dir: str, dry_run: bool = False):
    golden_path = Path(golden_dir) / "golden.json"
    if not golden_path.exists():
        print(f"  Skipping {golden_dir} — no golden.json")
        return

    with open(golden_path) as f:
        golden = json.load(f)

    source_path = Path(golden_dir) / golden["source_file"]
    source_text = source_path.read_text(encoding="utf-8")

    must_extract_dates = {
        e["encounter_date"]
        for e in golden["entries"]
        if e.get("must_extract") is True
    }

    # Remove existing may_extract and noise entries (we'll re-derive them)
    original_must = [e for e in golden["entries"] if e.get("must_extract") is True]
    old_may = [e for e in golden["entries"] if e.get("must_extract") == "may_extract"]
    old_noise = [e for e in golden["entries"] if e.get("must_extract") is False]

    print(f"  Current: {len(original_must)} must, {len(old_may)} may, {len(old_noise)} noise")

    # Scan for extra clinical encounters
    print(f"  Scanning source for extra clinical encounters...")
    extra_encounters = _scan_for_extra_encounters(source_text, must_extract_dates)
    print(f"  Found {len(extra_encounters)} extra encounter-like segments")

    may_extract_entries = []
    next_idx = len(original_must)
    extra_dates = set()
    for enc in extra_encounters:
        d = enc["date"]
        if d in extra_dates or d in must_extract_dates:
            continue
        extra_dates.add(d)
        may_extract_entries.append({
            "index": next_idx,
            "encounter_date": d,
            "facility_name": enc.get("facility", "Unknown"),
            "provider_name": "Not specified",
            "visit_type": enc.get("description", "Unknown"),
            "must_extract": "may_extract",
            "key_fields": {},
        })
        next_idx += 1
        print(f"    + may_extract: {d} | {enc.get('facility', '?')} | {enc.get('description', '?')}")

    # Re-derive noise dates (excluding must_extract and may_extract dates)
    all_known_dates = must_extract_dates | extra_dates
    noise_dates = _extract_noise_dates(source_text, all_known_dates)

    noise_entries = []
    for i, nd in enumerate(noise_dates):
        noise_entries.append({
            "index": next_idx + i,
            "encounter_date": nd,
            "facility_name": "NOISE",
            "provider_name": "NOISE",
            "visit_type": "administrative/non-clinical",
            "must_extract": False,
            "key_fields": {},
        })

    print(f"  New: {len(original_must)} must, {len(may_extract_entries)} may, {len(noise_entries)} noise")

    if dry_run:
        print(f"  [DRY RUN] Would update {golden_path}")
        return

    golden["entries"] = original_must + may_extract_entries + noise_entries
    golden["total_may_extract"] = len(may_extract_entries)
    golden["total_noise"] = len(noise_entries)

    # Backup original
    backup_path = golden_path.with_suffix(".json.bak")
    if not backup_path.exists():
        import shutil
        shutil.copy2(golden_path, backup_path)
        print(f"  Backed up to {backup_path}")

    with open(golden_path, "w") as f:
        json.dump(golden, f, indent=2)
    print(f"  Updated {golden_path}")


def main():
    dry_run = "--dry-run" in sys.argv

    for gd in GOLDEN_DIRS:
        print(f"\n=== {gd} ===")
        patch_golden(gd, dry_run=dry_run)

    if not dry_run:
        print(f"\nDone. Run evaluation to see updated results:")
        print(f"  bash run_golden_full.sh  (skip to evaluation section)")


if __name__ == "__main__":
    main()
