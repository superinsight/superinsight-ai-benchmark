#!/usr/bin/env python3
"""
Cross-validation between deterministic metrics and LLM-as-Judge hallucination scores.

Computes Pearson/Spearman correlation between:
- Semantic Fidelity (embedding cosine similarity) and Hallucination Score
- ROUGE-L F1 and Hallucination Score
- Content Fidelity (token overlap) and Hallucination Score

High correlation → LLM judge aligns with objective metrics → trustworthy.
Low correlation → possible judge bias.

Also computes Inter-Judge Agreement when multi-judge results are available.

Usage:
    python evaluate_cross_validation.py
    python evaluate_cross_validation.py --determ golden_outputs/deterministic_results.json \
                                        --halluc golden_outputs/hallucination_results.json
"""

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


def _pearson(x: List[float], y: List[float]) -> float:
    """Pearson correlation coefficient."""
    n = len(x)
    if n < 3:
        return float("nan")
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    sy = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if sx == 0 or sy == 0:
        return float("nan")
    return cov / (sx * sy)


def _spearman(x: List[float], y: List[float]) -> float:
    """Spearman rank correlation."""
    n = len(x)
    if n < 3:
        return float("nan")

    def _rank(vals):
        indexed = sorted(enumerate(vals), key=lambda p: p[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2 + 1
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx = _rank(x)
    ry = _rank(y)
    return _pearson(rx, ry)


def load_deterministic(path: str) -> Dict[str, Dict[str, dict]]:
    """Load deterministic results JSON.

    Expected structure from evaluate_deterministic.py --semantic:
    {golden_name: {model: {rouge_l_f1, token_overlap, avg_semantic_similarity, ...}}}
    """
    with open(path) as f:
        return json.load(f)


def load_hallucination(path: str) -> Dict[str, Dict[str, dict]]:
    """Load hallucination results JSON.

    Expected structure from evaluate_hallucination.py:
    {golden_name: {model: {score, hallucination_rate, per_judge, ...}}}
    """
    with open(path) as f:
        return json.load(f)


def compute_correlations(
    determ: Dict[str, Dict[str, dict]],
    halluc: Dict[str, Dict[str, dict]],
) -> Dict[str, Any]:
    """Compute correlations between deterministic and hallucination metrics."""
    results: Dict[str, Any] = {}

    metric_pairs = [
        ("avg_semantic_similarity", "Semantic Fidelity"),
        ("avg_rouge_l_f1", "ROUGE-L F1"),
        ("avg_token_overlap", "Token Overlap"),
    ]

    # Per-golden correlations
    for golden_name in sorted(set(determ.keys()) & set(halluc.keys())):
        d_models = determ[golden_name]
        h_models = halluc[golden_name]
        common = sorted(set(d_models.keys()) & set(h_models.keys()))

        if len(common) < 3:
            results[golden_name] = {"error": f"Too few models ({len(common)}) for correlation"}
            continue

        halluc_scores = []
        for m in common:
            hs = h_models[m].get("score", h_models[m].get("hallucination_score", -1))
            halluc_scores.append(hs)

        golden_result = {"models": common, "n": len(common), "correlations": {}}

        for metric_key, metric_label in metric_pairs:
            determ_values = []
            valid_halluc = []
            for i, m in enumerate(common):
                dv = d_models[m].get(metric_key)
                hv = halluc_scores[i]
                if dv is not None and dv >= 0 and hv >= 0:
                    determ_values.append(dv)
                    valid_halluc.append(hv)

            if len(determ_values) < 3:
                golden_result["correlations"][metric_key] = {
                    "label": metric_label, "n": len(determ_values),
                    "error": "insufficient data",
                }
                continue

            golden_result["correlations"][metric_key] = {
                "label": metric_label,
                "n": len(determ_values),
                "pearson": round(_pearson(determ_values, valid_halluc), 4),
                "spearman": round(_spearman(determ_values, valid_halluc), 4),
            }

        results[golden_name] = golden_result

    # Overall (pool all golden datasets)
    all_determ: Dict[str, List[float]] = defaultdict(list)
    all_halluc_for_metric: Dict[str, List[float]] = defaultdict(list)

    for golden_name in sorted(set(determ.keys()) & set(halluc.keys())):
        d_models = determ[golden_name]
        h_models = halluc[golden_name]
        common = sorted(set(d_models.keys()) & set(h_models.keys()))

        for m in common:
            hs = h_models[m].get("score", h_models[m].get("hallucination_score", -1))
            if hs < 0:
                continue
            for mk, _ in metric_pairs:
                dv = d_models[m].get(mk)
                if dv is not None and dv >= 0:
                    all_determ[mk].append(dv)
                    all_halluc_for_metric[mk].append(hs)

    overall = {"correlations": {}}
    for mk, ml in metric_pairs:
        dv = all_determ[mk]
        hv = all_halluc_for_metric[mk]
        if len(dv) < 3:
            overall["correlations"][mk] = {"label": ml, "n": len(dv), "error": "insufficient data"}
            continue
        overall["correlations"][mk] = {
            "label": ml,
            "n": len(dv),
            "pearson": round(_pearson(dv, hv), 4),
            "spearman": round(_spearman(dv, hv), 4),
        }
    results["_overall"] = overall

    # Inter-judge agreement (if multi-judge)
    judge_agreements = []
    for golden_name in halluc.values():
        for m_data in golden_name.values():
            if isinstance(m_data, dict) and "inter_judge_agreement" in m_data:
                judge_agreements.append(m_data["inter_judge_agreement"])

    if judge_agreements:
        mean_agree = sum(judge_agreements) / len(judge_agreements)
        results["_inter_judge"] = {
            "mean_agreement": round(mean_agree, 4),
            "n_evaluations": len(judge_agreements),
            "min": round(min(judge_agreements), 4),
            "max": round(max(judge_agreements), 4),
        }

    return results


def print_report(results: Dict[str, Any]):
    """Print a human-readable report."""
    print("\n" + "=" * 80)
    print("  CROSS-VALIDATION REPORT: Deterministic vs LLM-as-Judge")
    print("=" * 80)

    def _interp(r: float) -> str:
        if math.isnan(r):
            return "N/A"
        ar = abs(r)
        if ar >= 0.7:
            return "strong"
        if ar >= 0.4:
            return "moderate"
        if ar >= 0.2:
            return "weak"
        return "negligible"

    # Overall
    overall = results.get("_overall", {})
    if overall:
        print("\n--- Overall (all golden datasets pooled) ---")
        print(f"  {'Metric':25s}  {'Pearson':>8s}  {'Spearman':>8s}  {'Interp':>12s}  {'N':>4s}")
        print(f"  {'-' * 65}")
        for mk, data in overall.get("correlations", {}).items():
            if "error" in data:
                print(f"  {data['label']:25s}  {'---':>8s}  {'---':>8s}  {data['error']:>12s}  {data['n']:4d}")
            else:
                p = data["pearson"]
                s = data["spearman"]
                print(f"  {data['label']:25s}  {p:8.3f}  {s:8.3f}  {_interp(p):>12s}  {data['n']:4d}")

    # Per golden
    for golden_name in sorted(k for k in results if not k.startswith("_")):
        gr = results[golden_name]
        if "error" in gr:
            print(f"\n--- {golden_name} --- {gr['error']}")
            continue
        print(f"\n--- {golden_name} (n={gr['n']}) ---")
        print(f"  {'Metric':25s}  {'Pearson':>8s}  {'Spearman':>8s}  {'Interp':>12s}")
        print(f"  {'-' * 60}")
        for mk, data in gr.get("correlations", {}).items():
            if "error" in data:
                print(f"  {data['label']:25s}  {'---':>8s}  {'---':>8s}  {data.get('error', ''):>12s}")
            else:
                p = data["pearson"]
                s = data["spearman"]
                print(f"  {data['label']:25s}  {p:8.3f}  {s:8.3f}  {_interp(p):>12s}")

    # Inter-judge agreement
    ij = results.get("_inter_judge")
    if ij:
        print(f"\n--- Inter-Judge Agreement ---")
        print(f"  Mean agreement: {ij['mean_agreement']:.1%}")
        print(f"  Range: {ij['min']:.1%} - {ij['max']:.1%}")
        print(f"  N evaluations: {ij['n_evaluations']}")

    # Summary
    print("\n--- Interpretation Guide ---")
    print("  Pearson > 0.7  → Strong: LLM judge aligns well with objective metrics")
    print("  Pearson 0.4-0.7 → Moderate: Reasonable alignment, some bias possible")
    print("  Pearson < 0.4  → Weak: Significant divergence, review judge behavior")
    print("  Agreement > 80% → Judges agree on most claims → reliable")
    print("  Agreement < 60% → High disagreement → results should be interpreted cautiously")


def main():
    parser = argparse.ArgumentParser(description="Cross-validate LLM judge against deterministic metrics")
    parser.add_argument(
        "--determ", type=str,
        default="golden_outputs/deterministic_results.json",
        help="Path to deterministic evaluation results",
    )
    parser.add_argument(
        "--halluc", type=str,
        default="golden_outputs/hallucination_results.json",
        help="Path to hallucination evaluation results",
    )
    parser.add_argument("--output", "-o", type=str, default="golden_outputs/cross_validation.json")
    args = parser.parse_args()

    if not os.path.isfile(args.determ):
        print(f"ERROR: Deterministic results not found: {args.determ}")
        print("  Run: python evaluate_deterministic.py --rounds 3 --semantic")
        sys.exit(1)
    if not os.path.isfile(args.halluc):
        print(f"ERROR: Hallucination results not found: {args.halluc}")
        print("  Run: python evaluate_hallucination.py --rounds 3 --judges all")
        sys.exit(1)

    determ = load_deterministic(args.determ)
    halluc = load_hallucination(args.halluc)

    print(f"Deterministic: {len(determ)} golden datasets")
    print(f"Hallucination: {len(halluc)} golden datasets")

    results = compute_correlations(determ, halluc)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {args.output}")

    print_report(results)


if __name__ == "__main__":
    main()
