#!/usr/bin/env python3
"""
Generate machine-readable leaderboard.json from all evaluation results.

Aggregates: golden F1, deterministic metrics, semantic fidelity,
hallucination score, cost, and latency into a single ranked leaderboard.

Usage:
    python generate_leaderboard.py
    python generate_leaderboard.py --output golden_outputs/leaderboard.json
"""

import argparse
import json
import os
from pathlib import Path

OUTPUT_BASE = "golden_outputs"


def _safe_load(path: str) -> dict:
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _avg_across_golden(data: dict, model: str, metric: str) -> float:
    """Average a metric across all golden datasets for a model."""
    vals = []
    for gn, models in data.items():
        if not isinstance(models, dict):
            continue
        m = models.get(model, {})
        if isinstance(m, dict) and metric in m:
            vals.append(m[metric])
    return sum(vals) / len(vals) if vals else None


def main():
    parser = argparse.ArgumentParser(description="Generate leaderboard.json")
    parser.add_argument("--output", "-o", default="golden_outputs/leaderboard.json")
    args = parser.parse_args()

    golden_agg = _safe_load(f"{OUTPUT_BASE}/golden_benchmark_aggregated.json")
    det_results = _safe_load(f"{OUTPUT_BASE}/deterministic_results.json")
    halluc_results = _safe_load(f"{OUTPUT_BASE}/hallucination_results.json")
    cost_report = _safe_load(f"{OUTPUT_BASE}/cost_latency_report.json")
    bootstrap = _safe_load(f"{OUTPUT_BASE}/bootstrap_results.json")

    all_models = set()
    for data in [golden_agg, det_results]:
        for gn, models in data.items():
            if isinstance(models, dict):
                all_models.update(models.keys())
    if cost_report:
        all_models.update(cost_report.keys())

    leaderboard = []
    for model in sorted(all_models):
        entry = {"model": model}

        f1 = _avg_across_golden(golden_agg, model, "f1")
        if f1 is not None:
            entry["avg_f1"] = round(f1, 4)

        f1_std = _avg_across_golden(golden_agg, model, "f1_std")
        if f1_std is not None:
            entry["avg_f1_std"] = round(f1_std, 4)

        precision = _avg_across_golden(golden_agg, model, "precision")
        if precision is not None:
            entry["avg_precision"] = round(precision, 4)

        recall = _avg_across_golden(golden_agg, model, "recall")
        if recall is not None:
            entry["avg_recall"] = round(recall, 4)

        for metric_key, entry_key in [
            ("avg_rouge_l_f1", "avg_rouge_l"),
            ("avg_semantic_similarity", "avg_semantic_fidelity"),
            ("avg_token_overlap", "avg_token_overlap"),
            ("formatting_score", "formatting_score"),
            ("chronological_score", "chronological_score"),
        ]:
            val = _avg_across_golden(det_results, model, metric_key)
            if val is not None:
                entry[entry_key] = round(val, 4)

        halluc_vals = []
        for gn, models in halluc_results.items():
            if not isinstance(models, dict):
                continue
            m = models.get(model, {})
            if isinstance(m, dict) and "score" in m:
                halluc_vals.append(m["score"])
        if halluc_vals:
            entry["avg_hallucination_score"] = round(sum(halluc_vals) / len(halluc_vals), 4)

        if model in cost_report:
            cr = cost_report[model]
            entry["avg_latency_seconds"] = cr.get("latency_seconds", {}).get("mean", 0)
            entry["total_tokens_mean"] = cr.get("total_tokens", {}).get("mean", 0)

        if bootstrap and "model_summary" in bootstrap:
            bs = bootstrap["model_summary"].get(model, {})
            if bs:
                entry["bootstrap_ci_95"] = bs.get("ci_95", [])

        composite = 0.0
        weights = {"avg_f1": 0.30, "avg_semantic_fidelity": 0.20,
                   "avg_hallucination_score": 0.20, "formatting_score": 0.10,
                   "chronological_score": 0.10, "avg_rouge_l": 0.10}
        total_w = 0
        for k, w in weights.items():
            v = entry.get(k)
            if v is not None:
                composite += v * w
                total_w += w
        if total_w > 0:
            entry["composite_score"] = round(composite / total_w, 4)

        leaderboard.append(entry)

    leaderboard.sort(key=lambda e: -e.get("composite_score", 0))
    for rank, entry in enumerate(leaderboard, 1):
        entry["rank"] = rank

    output = {
        "version": "2.0",
        "description": "Medical Chronology Extraction Benchmark Leaderboard",
        "metrics_description": {
            "avg_f1": "Average F1 score across 6 golden datasets, 3 rounds",
            "avg_precision": "Average precision",
            "avg_recall": "Average recall",
            "avg_rouge_l": "Average ROUGE-L F1 for content fidelity",
            "avg_semantic_fidelity": "Average embedding cosine similarity",
            "avg_hallucination_score": "Average hallucination-free rate (higher=better)",
            "formatting_score": "Markdown formatting compliance",
            "chronological_score": "Date ordering compliance",
            "composite_score": "Weighted composite (F1 30%, Semantic 20%, Halluc 20%, Format 10%, Chrono 10%, ROUGE 10%)",
            "avg_latency_seconds": "Mean generation latency (seconds)",
        },
        "leaderboard": leaderboard,
    }

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"{'Rank':>4s}  {'Model':25s}  {'Composite':>10s}  {'F1':>8s}  {'Semantic':>8s}  {'Halluc':>8s}  {'Latency':>8s}")
    print("-" * 90)
    for e in leaderboard:
        print(
            f"{e['rank']:4d}  {e['model']:25s}  "
            f"{e.get('composite_score', 0):9.4f}  "
            f"{e.get('avg_f1', 0):7.1%}  "
            f"{e.get('avg_semantic_fidelity', 0):7.4f}  "
            f"{e.get('avg_hallucination_score', 0):7.1%}  "
            f"{e.get('avg_latency_seconds', 0):6.1f}s"
        )

    print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()
