#!/usr/bin/env python3
"""
Error analysis: identify systematic failure patterns across models.

Analyzes missed entries (FN), false positives (FP), and noise inclusions
across all rounds and golden datasets to find common failure modes.

Usage:
    python evaluate_error_analysis.py
    python evaluate_error_analysis.py --output golden_outputs/error_analysis.json
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from synthesize_golden import evaluate_against_golden

GOLDEN_DIRS = [
    "golden/golden_a", "golden/golden_b", "golden/golden_c",
    "golden/golden_d", "golden/golden_e", "golden/golden_f",
]
OUTPUT_BASE = "golden_outputs"


def collect_errors() -> dict:
    """Collect all errors across rounds and datasets."""
    errors = {
        "missed_entries": [],   # FN
        "extra_entries": [],    # FP
        "noise_extracted": [],  # false inclusions
        "per_model_summary": defaultdict(lambda: {"fn": 0, "fp": 0, "noise": 0, "total_runs": 0}),
        "per_dataset_summary": defaultdict(lambda: {"fn": 0, "fp": 0, "noise": 0, "total_runs": 0}),
    }

    round_dirs = sorted([
        d for d in Path(OUTPUT_BASE).iterdir()
        if d.is_dir() and d.name.startswith("round_")
    ], key=lambda d: int(d.name.split("_")[1]))

    for rd in round_dirs:
        round_num = int(rd.name.split("_")[1])
        for golden_dir in GOLDEN_DIRS:
            golden_name = Path(golden_dir).name
            golden_path = f"{golden_dir}/golden.json"
            if not os.path.isfile(golden_path):
                continue
            output_dir = rd / golden_name
            if not output_dir.is_dir():
                continue

            for model_dir in sorted(output_dir.iterdir()):
                if not model_dir.is_dir():
                    continue
                out_file = model_dir / "output.md"
                if not out_file.is_file() or not out_file.read_text().strip():
                    continue

                model = model_dir.name
                md = out_file.read_text(encoding="utf-8")
                result = evaluate_against_golden(golden_path, md)

                ctx = {"model": model, "round": round_num, "dataset": golden_name}

                for entry in result.get("missed_entries", []):
                    errors["missed_entries"].append({**ctx, **entry})

                for entry in result.get("extra_entries", []):
                    errors["extra_entries"].append({**ctx, **entry})

                for entry in result.get("noise_extracted", []):
                    errors["noise_extracted"].append({**ctx, **entry})

                fn = result.get("false_negatives", 0)
                fp = result.get("false_positives", 0)
                noise = result.get("false_inclusions", 0)

                errors["per_model_summary"][model]["fn"] += fn
                errors["per_model_summary"][model]["fp"] += fp
                errors["per_model_summary"][model]["noise"] += noise
                errors["per_model_summary"][model]["total_runs"] += 1

                errors["per_dataset_summary"][golden_name]["fn"] += fn
                errors["per_dataset_summary"][golden_name]["fp"] += fp
                errors["per_dataset_summary"][golden_name]["noise"] += noise
                errors["per_dataset_summary"][golden_name]["total_runs"] += 1

    return errors


def analyze_patterns(errors: dict) -> dict:
    """Identify systematic patterns in errors."""
    missed_dates = Counter()
    missed_by_model = Counter()
    missed_by_dataset = Counter()
    fp_by_model = Counter()
    noise_by_model = Counter()

    for e in errors["missed_entries"]:
        missed_dates[e["date"]] += 1
        missed_by_model[e["model"]] += 1
        missed_by_dataset[e["dataset"]] += 1

    for e in errors["extra_entries"]:
        fp_by_model[e["model"]] += 1

    for e in errors["noise_extracted"]:
        noise_by_model[e["model"]] += 1

    consistently_missed = [
        {"date": date, "count": count, "fraction_of_runs": f"{count}/{len(errors['missed_entries'])}"}
        for date, count in missed_dates.most_common(10)
        if count >= 3
    ]

    return {
        "total_fn": len(errors["missed_entries"]),
        "total_fp": len(errors["extra_entries"]),
        "total_noise_inclusions": len(errors["noise_extracted"]),
        "consistently_missed_dates": consistently_missed,
        "fn_by_model": dict(missed_by_model.most_common()),
        "fn_by_dataset": dict(missed_by_dataset.most_common()),
        "fp_by_model": dict(fp_by_model.most_common()),
        "noise_by_model": dict(noise_by_model.most_common()),
        "hardest_datasets": sorted(
            errors["per_dataset_summary"].items(),
            key=lambda x: x[1]["fn"] + x[1]["fp"],
            reverse=True,
        ),
        "most_error_prone_models": sorted(
            errors["per_model_summary"].items(),
            key=lambda x: x[1]["fn"] + x[1]["fp"],
            reverse=True,
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Error analysis")
    parser.add_argument("--output", "-o", default="golden_outputs/error_analysis.json")
    args = parser.parse_args()

    print("Collecting errors across all rounds and datasets...")
    errors = collect_errors()

    patterns = analyze_patterns(errors)

    print(f"\n=== Error Summary ===")
    print(f"  Total FN (missed entries):    {patterns['total_fn']}")
    print(f"  Total FP (extra entries):     {patterns['total_fp']}")
    print(f"  Total Noise Inclusions:       {patterns['total_noise_inclusions']}")

    print(f"\n=== FN by Model (top 5) ===")
    for model, count in list(patterns["fn_by_model"].items())[:5]:
        print(f"  {model:25s}  FN={count}")

    print(f"\n=== FN by Dataset ===")
    for dataset, count in patterns["fn_by_dataset"].items():
        print(f"  {dataset:15s}  FN={count}")

    print(f"\n=== FP by Model (top 5) ===")
    for model, count in list(patterns["fp_by_model"].items())[:5]:
        print(f"  {model:25s}  FP={count}")

    if patterns["consistently_missed_dates"]:
        print(f"\n=== Consistently Missed Dates ===")
        for item in patterns["consistently_missed_dates"]:
            print(f"  {item['date']:15s}  missed {item['count']} times")

    output = {
        "patterns": patterns,
        "per_model_summary": dict(errors["per_model_summary"]),
        "per_dataset_summary": dict(errors["per_dataset_summary"]),
        "missed_entries_detail": errors["missed_entries"][:50],
        "extra_entries_detail": errors["extra_entries"][:50],
        "noise_extracted_detail": errors["noise_extracted"][:50],
    }

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()
