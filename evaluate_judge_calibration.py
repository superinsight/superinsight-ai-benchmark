#!/usr/bin/env python3
"""
Reference-based Calibration for LLM-as-Judge.

Tests each judge against known hallucination/supported claims to measure
judge accuracy (Precision, Recall, F1 for detecting hallucinations).

Usage:
    python evaluate_judge_calibration.py
    python evaluate_judge_calibration.py --judges gemini gpt claude
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).parent))

from src.judges.hallucination import HallucinationJudge, BATCH_HALLUCINATION_PROMPT
from src.judges.base import Verdict
from src.contracts.llm_backend import get_backend

CALIBRATION_PATH = "golden/calibration_claims.json"

JUDGE_CONFIGS = {
    "gemini": {"backend": "gemini", "model": "gemini-2.0-flash", "label": "Gemini 2.0 Flash"},
    "gpt": {"backend": "openai", "model": "gpt-5.4-mini", "label": "GPT-5.4 Mini"},
    "claude": {"backend": "anthropic", "model": "claude-opus-4-5-20251101", "label": "Claude Opus 4.5"},
}

PROMPT_TEMPLATE = """You are a fact-checking assistant. Verify if each claim is supported by the source text.

## Source Text
{source_text}

## Claims to Verify
{claims_list}

## Instructions
For each claim:
1. Check if the source text supports the claim
2. Consider semantic equivalence (e.g., "Type 2 Diabetes" = "Diabetes Mellitus Type 2")
3. Be strict: if the source doesn't mention something, mark as UNSUPPORTED
4. PARTIAL means the source partially supports but misses some details

## Response Format
Return a JSON array with exactly one entry per claim:
```json
[
  {{"id": 1, "verdict": "SUPPORTED", "confidence": 0.9, "reason": "Source states patient has diabetes"}},
  ...
]
```

Verdict options: SUPPORTED | UNSUPPORTED | PARTIAL

## Your Response (JSON only):"""


def run_calibration(
    judge_keys: List[str],
    verbose: bool = False,
) -> Dict[str, Any]:
    """Run calibration for each judge against known claims."""
    with open(CALIBRATION_PATH) as f:
        calib_data = json.load(f)

    claims = calib_data["claims"]

    claims_by_golden: Dict[str, list] = defaultdict(list)
    for c in claims:
        claims_by_golden[c["golden"]].append(c)

    results: Dict[str, Dict[str, Any]] = {}

    for jk in judge_keys:
        cfg = JUDGE_CONFIGS[jk]
        label = cfg["label"]
        print(f"\n{'=' * 60}")
        print(f"  Judge: {label}")
        print(f"{'=' * 60}")

        backend = get_backend(backend_name=cfg["backend"], model=cfg["model"])
        all_predictions: List[Tuple[str, str]] = []  # (ground_truth, predicted)

        for golden_name in sorted(claims_by_golden.keys()):
            source_path = f"golden/{golden_name}/synthetic_source.txt"
            if not os.path.isfile(source_path):
                print(f"  [skip] {source_path} not found")
                continue

            source_text = Path(source_path).read_text(encoding="utf-8")
            golden_claims = claims_by_golden[golden_name]

            claims_list = "\n".join(
                f"{i+1}. [{c['field_type']}] {c['text']}"
                for i, c in enumerate(golden_claims)
            )

            prompt = PROMPT_TEMPLATE.format(
                source_text=source_text,
                claims_list=claims_list,
            )

            print(f"\n  {golden_name}: {len(golden_claims)} claims ...", end=" ", flush=True)
            t0 = time.time()

            try:
                response = backend.generate(prompt)
                elapsed = time.time() - t0

                import re
                json_match = re.search(r'\[[\s\S]*\]', response)
                if not json_match:
                    print(f"ERROR: no JSON in response ({elapsed:.1f}s)")
                    for c in golden_claims:
                        all_predictions.append((c["ground_truth"], "ERROR"))
                    continue

                parsed = json.loads(json_match.group())
                results_by_id = {r.get("id", i+1): r for i, r in enumerate(parsed)}

                correct = 0
                for i, c in enumerate(golden_claims):
                    r = results_by_id.get(i + 1, {})
                    predicted = r.get("verdict", "ERROR").upper()

                    gt = c["ground_truth"]
                    match = "✓" if predicted == gt else "✗"
                    if predicted == gt:
                        correct += 1

                    all_predictions.append((gt, predicted))

                    if verbose:
                        print(f"\n    {match} Claim {i+1}: GT={gt}, Pred={predicted}")
                        print(f"      {c['text'][:80]}...")
                        print(f"      Reason: {r.get('reason', 'N/A')[:80]}")

                print(f"{correct}/{len(golden_claims)} correct ({elapsed:.1f}s)")

            except Exception as e:
                elapsed = time.time() - t0
                print(f"ERROR: {e} ({elapsed:.1f}s)")
                for c in golden_claims:
                    all_predictions.append((c["ground_truth"], "ERROR"))

        # Compute metrics
        tp = sum(1 for gt, pred in all_predictions if gt == "UNSUPPORTED" and pred == "UNSUPPORTED")
        fp = sum(1 for gt, pred in all_predictions if gt == "SUPPORTED" and pred == "UNSUPPORTED")
        fn = sum(1 for gt, pred in all_predictions if gt == "UNSUPPORTED" and pred in ("SUPPORTED", "PARTIAL"))
        tn = sum(1 for gt, pred in all_predictions if gt == "SUPPORTED" and pred in ("SUPPORTED", "PARTIAL"))

        total_gt_unsupported = sum(1 for gt, _ in all_predictions if gt == "UNSUPPORTED")
        total_gt_supported = sum(1 for gt, _ in all_predictions if gt == "SUPPORTED")
        errors = sum(1 for _, pred in all_predictions if pred == "ERROR")

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / len(all_predictions) if all_predictions else 0.0

        results[jk] = {
            "label": label,
            "total_claims": len(all_predictions),
            "gt_unsupported": total_gt_unsupported,
            "gt_supported": total_gt_supported,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "errors": errors,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "accuracy": round(accuracy, 4),
            "predictions": [
                {"ground_truth": gt, "predicted": pred}
                for gt, pred in all_predictions
            ],
        }

    return results


def print_report(results: Dict[str, Dict[str, Any]]):
    print("\n" + "=" * 80)
    print("  JUDGE CALIBRATION REPORT")
    print("  (Detecting hallucinations = UNSUPPORTED claims)")
    print("=" * 80)
    print(f"\n  {'Judge':25s}  {'Accuracy':>8s}  {'Precision':>9s}  {'Recall':>7s}  {'F1':>6s}  {'TP':>4s}  {'FP':>4s}  {'FN':>4s}  {'TN':>4s}  {'Err':>4s}")
    print(f"  {'-' * 85}")

    for jk in sorted(results.keys()):
        r = results[jk]
        print(
            f"  {r['label']:25s}  {r['accuracy']:7.1%}  {r['precision']:8.1%}  "
            f"{r['recall']:6.1%}  {r['f1']:5.1%}  "
            f"{r['tp']:4d}  {r['fp']:4d}  {r['fn']:4d}  {r['tn']:4d}  {r['errors']:4d}"
        )

    print("\n  Interpretation:")
    print("    Precision: Of claims flagged as hallucination, how many truly are?")
    print("    Recall: Of actual hallucinations, how many did the judge catch?")
    print("    F1 > 80%: Judge is reliable for hallucination detection")
    print("    F1 < 60%: Judge may miss hallucinations or over-flag")


def main():
    parser = argparse.ArgumentParser(description="Calibrate LLM judges against known claims")
    parser.add_argument(
        "--judges", nargs="+", default=["all"],
        help="Judge keys: gemini, gpt, claude, or 'all'",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--output", "-o", type=str, default="golden_outputs/judge_calibration.json")
    args = parser.parse_args()

    if "all" in args.judges:
        judge_keys = list(JUDGE_CONFIGS.keys())
    else:
        judge_keys = args.judges

    print(f"Running judge calibration with {len(judge_keys)} judges...")
    print(f"  Calibration claims: {CALIBRATION_PATH}")

    results = run_calibration(judge_keys, verbose=args.verbose)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {args.output}")

    print_report(results)


if __name__ == "__main__":
    main()
