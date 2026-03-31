#!/usr/bin/env python3
"""
Paired bootstrap significance test for benchmark model comparisons.

For each pair of models, tests whether the metric difference is statistically
significant using a paired bootstrap resampling approach over (golden_dataset, round)
sample units.

Supports two metrics:
  - f1:        Extraction F1 (default, computed live from golden.json)
  - composite: Weighted composite score assembled from pre-computed JSON files
               (F1 30% + Semantic 20% + Halluc 20% + Fmt 10% + Chrono 10% + ROUGE 10%)

Usage:
    python evaluate_bootstrap.py
    python evaluate_bootstrap.py --metric f1 --n-boot 10000
    python evaluate_bootstrap.py --metric composite
    python evaluate_bootstrap.py --output golden_outputs/bootstrap_results.json
"""

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from synthesize_golden import evaluate_against_golden

GOLDEN_DIRS = [
    "golden/golden_a", "golden/golden_b", "golden/golden_c",
    "golden/golden_d", "golden/golden_e", "golden/golden_f",
]
GOLDEN_NAMES = [Path(d).name for d in GOLDEN_DIRS]
OUTPUT_BASE = "golden_outputs"

COMPOSITE_WEIGHTS = {
    "f1": 0.30,
    "avg_semantic_similarity": 0.20,
    "halluc_score": 0.20,
    "formatting_score": 0.10,
    "chronological_score": 0.10,
    "avg_rouge_l_f1": 0.10,
}


def _safe_load(path: str) -> dict:
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return {}


def collect_scores(metric: str = "f1") -> dict:
    """Collect per-(round, golden) scores for each model.
    Returns {model: [(round, golden, score), ...]}
    """
    round_dirs = sorted([
        d for d in Path(OUTPUT_BASE).iterdir()
        if d.is_dir() and d.name.startswith("round_")
    ], key=lambda d: int(d.name.split("_")[1]))

    scores = defaultdict(list)
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
                md = out_file.read_text(encoding="utf-8")
                result = evaluate_against_golden(golden_path, md)
                scores[model_dir.name].append(
                    (round_num, golden_name, result.get(metric, 0.0))
                )
    return scores


def collect_composite_scores() -> dict:
    """Collect per-(round, golden) composite scores from pre-computed JSONs.

    Assembles composite = F1*0.30 + Semantic*0.20 + Halluc*0.20
                        + Fmt*0.10 + Chrono*0.10 + ROUGE*0.10

    Returns {model: [(round_idx, golden_name, composite_score), ...]}
    """
    golden_agg = _safe_load(f"{OUTPUT_BASE}/golden_benchmark_aggregated.json")
    det = _safe_load(f"{OUTPUT_BASE}/deterministic_results.json")
    halluc = _safe_load(f"{OUTPUT_BASE}/hallucination_results.json")

    if not golden_agg:
        print("  ERROR: golden_benchmark_aggregated.json not found")
        return {}
    if not det:
        print("  WARNING: deterministic_results.json not found — fmt/chrono/rouge/semantic will be 0")
    if not halluc:
        print("  WARNING: hallucination_results.json not found — halluc will be 0")

    all_models = set()
    for gn in GOLDEN_NAMES:
        all_models.update(golden_agg.get(gn, {}).keys())

    scores = defaultdict(list)
    for model in sorted(all_models):
        for gn in GOLDEN_NAMES:
            g = golden_agg.get(gn, {}).get(model, {})
            d = det.get(gn, {}).get(model, {})
            h = halluc.get(gn, {}).get(model, {})

            f1_vals = g.get("f1_values", [])
            fmt_vals = d.get("formatting_score_values", [])
            chrono_vals = d.get("chronological_score_values", [])
            rouge_vals = d.get("avg_rouge_l_f1_values", [])
            semantic_vals = d.get("avg_semantic_similarity_values", [])
            halluc_vals = h.get("score_values", [])

            n = min(len(f1_vals),
                    len(fmt_vals) if fmt_vals else len(f1_vals),
                    len(chrono_vals) if chrono_vals else len(f1_vals),
                    len(rouge_vals) if rouge_vals else len(f1_vals),
                    len(semantic_vals) if semantic_vals else len(f1_vals),
                    len(halluc_vals) if halluc_vals else len(f1_vals))

            for i in range(n):
                composite = (
                    f1_vals[i] * COMPOSITE_WEIGHTS["f1"]
                    + (semantic_vals[i] if i < len(semantic_vals) else 0) * COMPOSITE_WEIGHTS["avg_semantic_similarity"]
                    + (halluc_vals[i] if i < len(halluc_vals) else 0) * COMPOSITE_WEIGHTS["halluc_score"]
                    + (fmt_vals[i] if i < len(fmt_vals) else 0) * COMPOSITE_WEIGHTS["formatting_score"]
                    + (chrono_vals[i] if i < len(chrono_vals) else 0) * COMPOSITE_WEIGHTS["chronological_score"]
                    + (rouge_vals[i] if i < len(rouge_vals) else 0) * COMPOSITE_WEIGHTS["avg_rouge_l_f1"]
                )
                scores[model].append((i + 1, gn, round(composite, 6)))

    return scores


def paired_bootstrap_test(
    scores_a: list, scores_b: list, n_boot: int = 10000, seed: int = 42
) -> dict:
    """Paired bootstrap test between two models.
    scores_a/b: list of (round, golden, score) tuples.
    Returns p-value, mean_diff, ci_lower, ci_upper.
    """
    key_to_a = {(r, g): s for r, g, s in scores_a}
    key_to_b = {(r, g): s for r, g, s in scores_b}
    common_keys = sorted(set(key_to_a.keys()) & set(key_to_b.keys()))

    if len(common_keys) < 3:
        return {"p_value": None, "mean_diff": None, "n_samples": len(common_keys),
                "note": "insufficient paired samples"}

    diffs = np.array([key_to_a[k] - key_to_b[k] for k in common_keys])
    observed_diff = np.mean(diffs)

    rng = np.random.RandomState(seed)
    n = len(diffs)
    boot_diffs = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.randint(0, n, size=n)
        boot_diffs[i] = np.mean(diffs[idx])

    if observed_diff >= 0:
        p_value = np.mean(boot_diffs <= 0)
    else:
        p_value = np.mean(boot_diffs >= 0)

    ci_lower = float(np.percentile(boot_diffs, 2.5))
    ci_upper = float(np.percentile(boot_diffs, 97.5))

    return {
        "mean_diff": round(float(observed_diff), 4),
        "p_value": round(float(p_value), 4),
        "ci_95_lower": round(ci_lower, 4),
        "ci_95_upper": round(ci_upper, 4),
        "significant_at_005": bool(p_value < 0.05),
        "n_samples": n,
        "effect_size_cohens_d": round(
            float(observed_diff / np.std(diffs, ddof=1)) if np.std(diffs, ddof=1) > 0 else 0, 4
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Paired bootstrap significance test")
    parser.add_argument("--metric", default="composite",
                        help="Metric to test: 'composite' (default) or any golden metric like 'f1'")
    parser.add_argument("--n-boot", type=int, default=10000, help="Bootstrap iterations")
    parser.add_argument("--output", "-o", default="golden_outputs/bootstrap_results.json")
    parser.add_argument("--top-n", type=int, default=0,
                        help="Only test top N models by mean score (0=all)")
    args = parser.parse_args()

    print(f"Collecting {args.metric} scores across all rounds and datasets...")
    if args.metric == "composite":
        scores = collect_composite_scores()
    else:
        scores = collect_scores(args.metric)
    print(f"  Found {len(scores)} models")
    for m, s in sorted(scores.items()):
        vals = [v for _, _, v in s]
        print(f"    {m:25s}  n={len(s):2d}  mean={np.mean(vals):.4f}  std={np.std(vals, ddof=1):.4f}")

    models = sorted(scores.keys(), key=lambda m: -np.mean([v for _, _, v in scores[m]]))
    if args.top_n > 0:
        models = models[:args.top_n]

    print(f"\nRunning paired bootstrap tests ({args.n_boot} iterations)...")
    results = {
        "metric": args.metric,
        "n_bootstrap": args.n_boot,
        "model_summary": {},
        "pairwise_tests": [],
    }

    for m in models:
        vals = [v for _, _, v in scores[m]]
        results["model_summary"][m] = {
            "mean": round(float(np.mean(vals)), 4),
            "std": round(float(np.std(vals, ddof=1)), 4),
            "n_samples": len(vals),
            "ci_95": [
                round(float(np.percentile(vals, 2.5)), 4),
                round(float(np.percentile(vals, 97.5)), 4),
            ],
        }

    for m_a, m_b in combinations(models, 2):
        test = paired_bootstrap_test(scores[m_a], scores[m_b], args.n_boot)
        test["model_a"] = m_a
        test["model_b"] = m_b
        results["pairwise_tests"].append(test)
        sig = "***" if test.get("significant_at_005") else "   "
        diff = test.get("mean_diff", 0) or 0
        p = test.get("p_value")
        p_str = f"p={p:.4f}" if p is not None else "p=N/A"
        print(f"  {m_a:25s} vs {m_b:25s}  diff={diff:+.4f}  {p_str}  {sig}")

    n_sig = sum(1 for t in results["pairwise_tests"] if t.get("significant_at_005"))
    n_total = len(results["pairwise_tests"])
    print(f"\n{n_sig}/{n_total} pairs significantly different at p<0.05")

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()
