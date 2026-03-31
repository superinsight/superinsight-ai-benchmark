#!/usr/bin/env python3
"""
Aggregate cost and latency metrics from model metadata.json files.

Reads metadata.json from each model output directory across all rounds
and golden datasets, then computes per-model averages for:
  - Latency (seconds)
  - Prompt tokens
  - Completion tokens
  - Total tokens

Usage:
    python evaluate_cost_latency.py
    python evaluate_cost_latency.py --output golden_outputs/cost_latency_report.json
"""

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

import numpy as np

OUTPUT_BASE = "golden_outputs"

PRICING = {
    "gemini-2.5-pro":    {"input": 1.25 / 1e6, "output": 10.0 / 1e6},
    "gemini-2.5-flash":  {"input": 0.15 / 1e6, "output": 0.60 / 1e6},
    "gemini-3-flash":    {"input": 0.15 / 1e6, "output": 0.60 / 1e6},
    "gemini-3.1-pro":    {"input": 1.25 / 1e6, "output": 10.0 / 1e6},
    "gpt-5.4":           {"input": 2.50 / 1e6, "output": 10.0 / 1e6},
    "gpt-5.4-mini":      {"input": 0.40 / 1e6, "output": 1.60 / 1e6},
    "gpt-5.4-pro":       {"input": 10.0 / 1e6, "output": 40.0 / 1e6},
    "claude-opus-4.5":   {"input": 15.0 / 1e6, "output": 75.0 / 1e6},
    "claude-opus-4.6":   {"input": 3.00 / 1e6, "output": 15.0 / 1e6},
    "qwen3-235b":        {"input": 0.50 / 1e6, "output": 2.00 / 1e6},
    "minimax-m2.5":      {"input": 0.50 / 1e6, "output": 2.00 / 1e6},
}


def collect_metadata() -> dict:
    """Collect all metadata.json files. Returns {model: [metadata_dicts]}."""
    data = defaultdict(list)
    round_dirs = sorted([
        d for d in Path(OUTPUT_BASE).iterdir()
        if d.is_dir() and d.name.startswith("round_")
    ], key=lambda d: int(d.name.split("_")[1]))

    for rd in round_dirs:
        for golden_dir in sorted(rd.iterdir()):
            if not golden_dir.is_dir() or not golden_dir.name.startswith("golden_"):
                continue
            for model_dir in sorted(golden_dir.iterdir()):
                if not model_dir.is_dir():
                    continue
                meta_file = model_dir / "metadata.json"
                if not meta_file.is_file():
                    continue
                try:
                    meta = json.loads(meta_file.read_text())
                    if meta.get("status") == "success":
                        data[model_dir.name].append(meta)
                except (json.JSONDecodeError, KeyError):
                    continue
    return data


def compute_report(data: dict) -> dict:
    """Compute per-model cost/latency summary."""
    report = {}
    for model in sorted(data.keys()):
        metas = data[model]
        durations = [m["duration_seconds"] for m in metas if "duration_seconds" in m]
        prompt_toks = [m["prompt_tokens"] for m in metas if "prompt_tokens" in m]
        comp_toks = [m["completion_tokens"] for m in metas if "completion_tokens" in m]
        total_toks = [m["total_tokens"] for m in metas if "total_tokens" in m]

        pricing = PRICING.get(model, {"input": 0, "output": 0})
        costs = []
        for m in metas:
            pt = m.get("prompt_tokens", 0) or 0
            ct = m.get("completion_tokens", 0) or 0
            cost = pt * pricing["input"] + ct * pricing["output"]
            costs.append(cost)

        def _stats(arr):
            if not arr:
                return {"mean": 0, "std": 0, "min": 0, "max": 0, "n": 0}
            a = np.array(arr)
            return {
                "mean": round(float(np.mean(a)), 2),
                "std": round(float(np.std(a, ddof=1)) if len(a) > 1 else 0, 2),
                "min": round(float(np.min(a)), 2),
                "max": round(float(np.max(a)), 2),
                "n": len(a),
            }

        report[model] = {
            "latency_seconds": _stats(durations),
            "prompt_tokens": _stats(prompt_toks),
            "completion_tokens": _stats(comp_toks),
            "total_tokens": _stats(total_toks),
            "estimated_cost_usd": _stats(costs),
            "total_runs": len(metas),
        }

    return report


def main():
    parser = argparse.ArgumentParser(description="Cost and latency report")
    parser.add_argument("--output", "-o", default="golden_outputs/cost_latency_report.json")
    args = parser.parse_args()

    print("Collecting metadata from all rounds and golden datasets...")
    data = collect_metadata()
    print(f"  Found {len(data)} models, {sum(len(v) for v in data.values())} total runs\n")

    report = compute_report(data)

    print(f"{'Model':25s}  {'Latency(s)':>12s}  {'Prompt Tok':>12s}  {'Comp Tok':>12s}  {'Cost/run':>10s}  {'Runs':>5s}")
    print("-" * 90)
    for model in sorted(report.keys()):
        r = report[model]
        lat = r["latency_seconds"]
        pt = r["prompt_tokens"]
        ct = r["completion_tokens"]
        cost = r["estimated_cost_usd"]
        print(
            f"{model:25s}  "
            f"{lat['mean']:8.1f}±{lat['std']:4.1f}  "
            f"{pt['mean']:8.0f}±{pt['std']:4.0f}  "
            f"{ct['mean']:8.0f}±{ct['std']:4.0f}  "
            f"${cost['mean']:7.4f}  "
            f"{r['total_runs']:5d}"
        )

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()
