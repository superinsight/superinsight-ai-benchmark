#!/usr/bin/env python3
"""
Re-evaluate all existing model outputs against golden.json files.
Supports multi-round evaluation: looks for golden_outputs/round_N/ directories.

Usage:
    # Evaluate single-round (legacy: golden_outputs/golden_a/model/)
    python evaluate_golden_only.py

    # Evaluate multi-round (golden_outputs/round_1/golden_a/model/, etc.)
    python evaluate_golden_only.py --rounds 3

    # Evaluate specific round only
    python evaluate_golden_only.py --round 2
"""

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from synthesize_golden import evaluate_against_golden

GOLDEN_DIRS = [
    "golden/golden_a", "golden/golden_b", "golden/golden_c",
    "golden/golden_d", "golden/golden_e", "golden/golden_f",
]
OUTPUT_BASE = "golden_outputs"


def evaluate_single_dir(output_base: str, verbose: bool = True) -> dict:
    """Evaluate all models in a single output directory. Returns {golden_name: {model: result}}."""
    all_results = {}

    for golden_dir in GOLDEN_DIRS:
        golden_name = Path(golden_dir).name
        golden_path = f"{golden_dir}/golden.json"
        output_dir = f"{output_base}/{golden_name}"

        if not os.path.isfile(golden_path):
            continue

        with open(golden_path) as f:
            g = json.load(f)

        must = sum(1 for e in g["entries"] if e.get("must_extract") is True)
        may = sum(1 for e in g["entries"] if e.get("must_extract") == "may_extract")
        noise = sum(1 for e in g["entries"] if e.get("must_extract") is False)

        if verbose:
            print(f"\n--- {golden_name} (style={g['style']}, must={must}, may={may}, noise={noise}) ---")
            print(f"  {'Model':25s}  {'Prec':>6s}  {'Recall':>6s}  {'F1':>6s}  {'FI':>6s}  {'TP':>3s}  {'FP':>3s}  {'FN':>3s}  {'May':>3s}  {'#':>3s}")

        results = {}
        if not os.path.isdir(output_dir):
            if verbose:
                print(f"  No outputs directory: {output_dir}")
            continue

        for model in sorted(os.listdir(output_dir)):
            output_file = os.path.join(output_dir, model, "output.md")
            if not os.path.isfile(output_file):
                continue
            md = Path(output_file).read_text(encoding="utf-8")
            if not md.strip():
                if verbose:
                    print(f"  {model:25s}  (empty output)")
                continue
            r = evaluate_against_golden(golden_path, md)
            results[model] = r

            if verbose:
                may_m = r.get("may_extract_matched", 0)
                print(
                    f"  {model:25s}  {r['precision']:5.1%}  {r['recall']:5.1%}  "
                    f"{r['f1']:5.1%}  {r['false_inclusion_rate']:5.1%}  "
                    f"{r['true_positives']:3d}  {r['false_positives']:3d}  "
                    f"{r['false_negatives']:3d}  {may_m:3d}  "
                    f"{r['total_model_entries']:3d}"
                )

        all_results[golden_name] = results

    return all_results


def print_summary(all_results: dict, label: str = ""):
    """Print cross-dataset F1 summary."""
    title = f"CROSS-DATASET SUMMARY (F1){f' — {label}' if label else ''}"
    print(f"\n=== {title} ===")
    models_seen = set()
    active_gn = sorted(all_results.keys())
    for res in all_results.values():
        models_seen.update(res.keys())

    header = f"  {'Model':25s}" + "".join(f"  {gn:>12s}" for gn in active_gn) + f"  {'AVG':>9s}"
    print(header)
    for model in sorted(models_seen):
        f1s = []
        print(f"  {model:25s}", end="")
        for gn in active_gn:
            r = all_results.get(gn, {}).get(model)
            if r:
                f1s.append(r["f1"])
                print(f"  {r['f1']:11.1%}", end="")
            else:
                print(f"  {'—':>12s}", end="")
        avg = sum(f1s) / len(f1s) if f1s else 0
        print(f"  {avg:8.1%}")


def aggregate_rounds(round_results: list) -> dict:
    """Aggregate results across multiple rounds. Returns {golden_name: {model: aggregated_result}}."""
    aggregated = {}
    golden_names = set()
    for rr in round_results:
        golden_names.update(rr.keys())

    for gn in sorted(golden_names):
        model_scores = defaultdict(lambda: defaultdict(list))
        for rr in round_results:
            if gn not in rr:
                continue
            for model, result in rr[gn].items():
                for metric in ["precision", "recall", "f1", "false_inclusion_rate",
                               "true_positives", "false_positives", "false_negatives",
                               "total_model_entries", "may_extract_matched"]:
                    val = result.get(metric, 0)
                    model_scores[model][metric].append(val)

        agg = {}
        for model, metrics in model_scores.items():
            agg_result = {}
            for metric, values in metrics.items():
                mean = sum(values) / len(values)
                if len(values) > 1:
                    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
                    std = math.sqrt(variance)
                else:
                    std = 0.0
                agg_result[metric] = mean
                agg_result[f"{metric}_std"] = std
                agg_result[f"{metric}_values"] = values
            agg_result["num_rounds"] = len(metrics.get("f1", []))
            agg[model] = agg_result
        aggregated[gn] = agg

    return aggregated


def print_multi_round_summary(aggregated: dict, num_rounds: int):
    """Print aggregated multi-round summary with mean ± std."""
    print(f"\n{'='*80}")
    print(f"  MULTI-ROUND SUMMARY ({num_rounds} rounds, mean ± std)")
    print(f"{'='*80}")

    models_seen = set()
    for res in aggregated.values():
        models_seen.update(res.keys())

    active_gn = sorted(aggregated.keys())

    # Per-golden breakdown
    for gn in active_gn:
        print(f"\n--- {gn} ---")
        print(f"  {'Model':25s}  {'Precision':>12s}  {'Recall':>12s}  {'F1':>12s}  {'FI Rate':>12s}")
        for model in sorted(models_seen):
            r = aggregated[gn].get(model)
            if not r:
                continue
            def _fmt(metric):
                m = r.get(metric, 0)
                s = r.get(f"{metric}_std", 0)
                return f"{m:5.1%}±{s:4.1%}"
            print(f"  {model:25s}  {_fmt('precision'):>12s}  {_fmt('recall'):>12s}  {_fmt('f1'):>12s}  {_fmt('false_inclusion_rate'):>12s}")

    # Overall F1 ranking
    print(f"\n=== OVERALL F1 RANKING ({num_rounds} rounds) ===")
    header = f"  {'Model':25s}" + "".join(f"  {gn:>12s}" for gn in active_gn) + f"  {'AVG':>12s}"
    print(header)

    model_avgs = {}
    for model in sorted(models_seen):
        f1_means = []
        print(f"  {model:25s}", end="")
        for gn in active_gn:
            r = aggregated.get(gn, {}).get(model)
            if r:
                m = r.get("f1", 0)
                s = r.get("f1_std", 0)
                f1_means.append(m)
                print(f"  {m:5.1%}±{s:4.1%}", end="")
            else:
                print(f"  {'—':>12s}", end="")
        avg = sum(f1_means) / len(f1_means) if f1_means else 0
        model_avgs[model] = avg
        print(f"  {avg:10.1%}")

    # Sorted ranking
    print(f"\n  Final Ranking:")
    for rank, (model, avg) in enumerate(sorted(model_avgs.items(), key=lambda x: -x[1]), 1):
        print(f"    {rank}. {model:25s}  AVG F1 = {avg:.1%}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate golden benchmark results")
    parser.add_argument("--rounds", "-n", type=int, default=0,
                        help="Number of rounds to aggregate (0=auto-detect)")
    parser.add_argument("--round", "-r", type=int, default=0,
                        help="Evaluate a specific single round only")
    args = parser.parse_args()

    # Detect round directories
    round_dirs = sorted([
        d for d in Path(OUTPUT_BASE).iterdir()
        if d.is_dir() and d.name.startswith("round_")
    ], key=lambda d: int(d.name.split("_")[1]))

    if args.round > 0:
        # Single specific round
        round_dir = f"{OUTPUT_BASE}/round_{args.round}"
        print(f"\n=== Evaluating Round {args.round} ===")
        results = evaluate_single_dir(round_dir)
        print_summary(results, f"Round {args.round}")
        out_path = f"{round_dir}/golden_benchmark_results.json"
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved: {out_path}")
        return

    if round_dirs:
        # Multi-round mode
        num_rounds = args.rounds if args.rounds > 0 else len(round_dirs)
        round_dirs = round_dirs[:num_rounds]
        print(f"\nFound {len(round_dirs)} round(s): {[d.name for d in round_dirs]}")

        all_round_results = []
        for rd in round_dirs:
            round_num = rd.name.split("_")[1]
            print(f"\n{'='*60}")
            print(f"  Round {round_num}")
            print(f"{'='*60}")
            results = evaluate_single_dir(str(rd), verbose=True)
            print_summary(results, f"Round {round_num}")
            all_round_results.append(results)

            out_path = f"{rd}/golden_benchmark_results.json"
            with open(out_path, "w") as f:
                json.dump(results, f, indent=2)

        # Aggregate
        aggregated = aggregate_rounds(all_round_results)
        print_multi_round_summary(aggregated, len(round_dirs))

        out_path = f"{OUTPUT_BASE}/golden_benchmark_aggregated.json"
        with open(out_path, "w") as f:
            json.dump(aggregated, f, indent=2, default=str)
        print(f"\nSaved: {out_path}")

    else:
        # Legacy single-round mode (golden_outputs/golden_a/model/)
        print("\n(Single-round mode — no round_N directories found)")
        results = evaluate_single_dir(OUTPUT_BASE)
        print_summary(results)
        out_path = f"{OUTPUT_BASE}/golden_benchmark_results.json"
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
