#!/usr/bin/env python3
"""
Hallucination evaluation for golden outputs using Multi-Judge LLM panel.

Runs 3 independent judges (Gemini / GPT / Claude) against every output.md,
then aggregates via Majority Vote to reduce single-judge bias.

Usage:
    python evaluate_hallucination.py --rounds 3
    python evaluate_hallucination.py --rounds 1 --judges gemini   # single judge
    python evaluate_hallucination.py --rounds 3 --judges all      # 3-judge panel

    # Incremental: only evaluate a new model, skip existing results
    python evaluate_hallucination.py --rounds 3 --judges all --models my-new-model --incremental
"""

import argparse
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).parent))

from src.judges.hallucination import verify_hallucinations, HallucinationResult
from src.judges.base import Verdict, JudgeVerdict
from src.contracts.llm_backend import get_backend, LLMBackend

GOLDEN_DIRS = [
    "golden/golden_a", "golden/golden_b", "golden/golden_c",
    "golden/golden_d", "golden/golden_e", "golden/golden_f",
]
OUTPUT_BASE = "golden_outputs"

JUDGE_CONFIGS = {
    "gemini": {"backend": "gemini", "model": "gemini-2.0-flash", "label": "Gemini 2.0 Flash"},
    "gpt": {"backend": "openai", "model": "gpt-5.4-mini", "label": "GPT-5.4 Mini"},
    "claude": {"backend": "anthropic", "model": "claude-opus-4-5-20251101", "label": "Claude Opus 4.5"},
}


def _aggregate_metric(values: List[float]) -> Tuple[float, float]:
    if not values:
        return 0.0, 0.0
    mean = sum(values) / len(values)
    if len(values) < 2:
        return mean, 0.0
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return mean, math.sqrt(variance)


def _majority_vote(verdicts: List[str]) -> str:
    """Majority vote across judges. Returns the most common verdict."""
    counts = Counter(v for v in verdicts if v not in ("ERROR", "INCONCLUSIVE"))
    if not counts:
        return "ERROR"
    winner, count = counts.most_common(1)[0]
    return winner


def _create_backend(judge_key: str) -> LLMBackend:
    cfg = JUDGE_CONFIGS[judge_key]
    return get_backend(backend_name=cfg["backend"], model=cfg["model"])


def run_single_judge(
    judge_key: str,
    output_md: str,
    source_text: str,
    max_claims: int = 200,
    batch_size: int = 15,
    max_workers: int = 5,
) -> HallucinationResult:
    """Run a single judge on one output."""
    backend = _create_backend(judge_key)
    return verify_hallucinations(
        output_md=output_md,
        source_text=source_text,
        max_claims=max_claims,
        batch_size=batch_size,
        max_workers=max_workers,
        parallel=True,
        verbose=False,
        backend=backend,
    )


def run_multi_judge(
    judge_keys: List[str],
    output_md: str,
    source_text: str,
    max_claims: int = 200,
    batch_size: int = 15,
    max_workers: int = 5,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Run multiple judges and aggregate via Majority Vote.

    Returns dict with per-judge results and majority-vote aggregated result.
    """
    per_judge: Dict[str, dict] = {}
    all_verdicts_by_claim: Dict[int, Dict[str, str]] = defaultdict(dict)

    for jk in judge_keys:
        label = JUDGE_CONFIGS[jk]["label"]
        t0 = time.time()
        try:
            result = run_single_judge(
                jk, output_md, source_text, max_claims, batch_size, max_workers,
            )
            rd = result.to_dict()
            elapsed = time.time() - t0
            if verbose:
                print(
                    f"    [{label}] score={rd['score']:.1%} "
                    f"({rd['supported_claims']}S/{rd['unsupported_claims']}U/{rd['partial_claims']}P) "
                    f"{elapsed:.1f}s"
                )
            per_judge[jk] = rd
            for i, v in enumerate(result.verdicts):
                all_verdicts_by_claim[i][jk] = v.verdict.value
        except Exception as e:
            elapsed = time.time() - t0
            if verbose:
                print(f"    [{label}] ERROR: {e} ({elapsed:.1f}s)")
            per_judge[jk] = {"score": -1.0, "error": str(e)}

    # Majority vote
    total = len(all_verdicts_by_claim)
    supported = 0
    unsupported = 0
    partial = 0
    agreements = 0

    for idx in sorted(all_verdicts_by_claim.keys()):
        judge_verdicts = all_verdicts_by_claim[idx]
        verdict_values = list(judge_verdicts.values())
        winner = _majority_vote(verdict_values)

        if winner == "SUPPORTED":
            supported += 1
        elif winner == "UNSUPPORTED":
            unsupported += 1
        elif winner == "PARTIAL":
            partial += 1

        valid = [v for v in verdict_values if v not in ("ERROR", "INCONCLUSIVE")]
        if len(valid) >= 2 and len(set(valid)) == 1:
            agreements += 1

    scorable = supported + unsupported + partial
    mv_score = (supported + partial * 0.5) / scorable if scorable > 0 else 1.0
    halluc_rate = unsupported / total if total > 0 else 0.0
    agreement_rate = agreements / total if total > 0 else 0.0

    return {
        "majority_vote": {
            "score": round(mv_score, 4),
            "hallucination_rate": round(halluc_rate, 4),
            "total_claims": total,
            "supported_claims": supported,
            "unsupported_claims": unsupported,
            "partial_claims": partial,
            "inter_judge_agreement": round(agreement_rate, 4),
        },
        "per_judge": per_judge,
    }


def _load_existing_results(output_path: str) -> Dict[str, Dict[str, List[dict]]]:
    """Load existing hallucination results file and reconstruct raw round data.

    Returns a dict like {golden_name: {model: [round_result, ...]}} that can be
    used to skip already-evaluated combinations.
    """
    if not os.path.isfile(output_path):
        return {}
    try:
        with open(output_path) as f:
            data = json.load(f)
        existing: Dict[str, Dict[str, List[dict]]] = {}
        for golden_name, models in data.items():
            if not isinstance(models, dict):
                continue
            existing[golden_name] = {}
            for model, info in models.items():
                if isinstance(info, dict) and info.get("num_rounds", 0) > 0:
                    existing[golden_name][model] = info["num_rounds"]
        return existing
    except (json.JSONDecodeError, KeyError):
        return {}


def evaluate_all(
    num_rounds: int = 3,
    judge_keys: List[str] = None,
    max_claims: int = 200,
    batch_size: int = 15,
    max_workers: int = 5,
    verbose: bool = False,
    golden_filter: List[str] = None,
    start_round: int = 1,
    model_filter: List[str] = None,
    existing_results_path: str = None,
) -> Dict[str, Any]:
    """Run hallucination evaluation across all rounds with multi-judge panel.

    Args:
        model_filter: If provided, only evaluate these model labels.
        existing_results_path: Path to existing results file; when provided,
            skip model/dataset combos that already have >= num_rounds evaluated.
    """
    if judge_keys is None:
        judge_keys = list(JUDGE_CONFIGS.keys())

    multi = len(judge_keys) > 1
    raw: Dict[str, Dict[str, List[dict]]] = defaultdict(lambda: defaultdict(list))

    cache: Dict[str, Dict[str, int]] = {}
    if existing_results_path:
        cache = _load_existing_results(existing_results_path)

    for round_idx in range(start_round, num_rounds + 1):
        round_dir = f"{OUTPUT_BASE}/round_{round_idx}"
        if not os.path.isdir(round_dir):
            if verbose:
                print(f"  [skip] {round_dir} not found")
            continue

        for golden_dir in GOLDEN_DIRS:
            golden_name = Path(golden_dir).name
            if golden_filter and golden_name not in golden_filter:
                continue
            source_path = f"{golden_dir}/synthetic_source.txt"
            output_dir = f"{round_dir}/{golden_name}"

            if not os.path.isfile(source_path) or not os.path.isdir(output_dir):
                continue

            source_text = Path(source_path).read_text(encoding="utf-8")

            for model in sorted(os.listdir(output_dir)):
                if model_filter and model not in model_filter:
                    continue
                output_file = os.path.join(output_dir, model, "output.md")
                if not os.path.isfile(output_file):
                    continue
                md = Path(output_file).read_text(encoding="utf-8")
                if not md.strip():
                    continue

                cached_rounds = cache.get(golden_name, {}).get(model, 0)
                if cached_rounds >= num_rounds:
                    print(f"  R{round_idx} {golden_name}/{model} [cached — {cached_rounds} rounds exist]", flush=True)
                    continue

                print(f"  R{round_idx} {golden_name}/{model} ...", flush=True)
                t0 = time.time()

                if multi:
                    result = run_multi_judge(
                        judge_keys, md, source_text,
                        max_claims, batch_size, max_workers, verbose,
                    )
                    elapsed = time.time() - t0
                    mv = result["majority_vote"]
                    print(
                        f"    [MV] score={mv['score']:.1%} "
                        f"({mv['supported_claims']}S/{mv['unsupported_claims']}U/{mv['partial_claims']}P) "
                        f"agree={mv['inter_judge_agreement']:.0%} "
                        f"{elapsed:.1f}s"
                    )
                    raw[golden_name][model].append(result)
                else:
                    jk = judge_keys[0]
                    try:
                        hr = run_single_judge(
                            jk, md, source_text, max_claims, batch_size, max_workers,
                        )
                        rd = hr.to_dict()
                        elapsed = time.time() - t0
                        print(
                            f"    score={rd['score']:.1%} "
                            f"({rd['supported_claims']}S/{rd['unsupported_claims']}U/{rd['partial_claims']}P) "
                            f"{elapsed:.1f}s"
                        )
                        raw[golden_name][model].append({
                            "majority_vote": {
                                "score": rd["score"],
                                "hallucination_rate": rd["unsupported_claims"] / rd["total_claims"] if rd["total_claims"] > 0 else 0,
                                "total_claims": rd["total_claims"],
                                "supported_claims": rd["supported_claims"],
                                "unsupported_claims": rd["unsupported_claims"],
                                "partial_claims": rd["partial_claims"],
                                "inter_judge_agreement": 1.0,
                            },
                            "per_judge": {jk: rd},
                        })
                    except Exception as e:
                        elapsed = time.time() - t0
                        print(f"    ERROR: {e} ({elapsed:.1f}s)")
                        raw[golden_name][model].append({
                            "majority_vote": {"score": -1.0, "error": str(e)},
                            "per_judge": {},
                        })

    # Aggregate across rounds
    aggregated: Dict[str, Dict[str, dict]] = defaultdict(dict)

    for golden_name in sorted(raw.keys()):
        for model in sorted(raw[golden_name].keys()):
            rounds = raw[golden_name][model]
            valid = [r for r in rounds if r["majority_vote"].get("score", -1) >= 0]
            n = len(valid)

            if n == 0:
                aggregated[golden_name][model] = {
                    "num_rounds": 0, "score": -1.0, "error": "all rounds failed",
                }
                continue

            mv_scores = [r["majority_vote"]["score"] for r in valid]
            mean_s, std_s = _aggregate_metric(mv_scores)

            total_claims = sum(r["majority_vote"].get("total_claims", 0) for r in valid)
            supported = sum(r["majority_vote"].get("supported_claims", 0) for r in valid)
            unsupported = sum(r["majority_vote"].get("unsupported_claims", 0) for r in valid)
            partial = sum(r["majority_vote"].get("partial_claims", 0) for r in valid)
            halluc_rate = unsupported / total_claims if total_claims > 0 else 0.0

            agree_values = [r["majority_vote"].get("inter_judge_agreement", 0) for r in valid]
            mean_agree, _ = _aggregate_metric(agree_values)

            per_judge_scores: Dict[str, List[float]] = defaultdict(list)
            for r in valid:
                for jk, jd in r.get("per_judge", {}).items():
                    if isinstance(jd, dict) and jd.get("score", -1) >= 0:
                        per_judge_scores[jk].append(jd["score"])

            per_judge_agg = {}
            for jk, scores in per_judge_scores.items():
                m, s = _aggregate_metric(scores)
                per_judge_agg[jk] = {"mean": round(m, 4), "std": round(s, 4)}

            aggregated[golden_name][model] = {
                "num_rounds": n,
                "score": round(mean_s, 4),
                "score_std": round(std_s, 4),
                "score_values": [round(s, 4) for s in mv_scores],
                "hallucination_rate": round(halluc_rate, 4),
                "total_claims": total_claims,
                "supported_claims": supported,
                "unsupported_claims": unsupported,
                "partial_claims": partial,
                "inter_judge_agreement": round(mean_agree, 4),
                "per_judge": per_judge_agg,
            }

    return dict(aggregated)


def print_summary(aggregated: Dict[str, Dict[str, dict]], multi: bool = True):
    for golden_name in sorted(aggregated.keys()):
        models = aggregated[golden_name]
        w = 110 if multi else 95
        print(f"\n{'=' * w}")
        print(f"  {golden_name}")
        print(f"{'=' * w}")

        header = f"  {'Model':25s}  {'MV Score':>8s}  {'±std':>6s}  {'HRate':>6s}"
        if multi:
            header += f"  {'Agree':>6s}"
            for jk in JUDGE_CONFIGS:
                if any(jk in m.get("per_judge", {}) for m in models.values()):
                    header += f"  {JUDGE_CONFIGS[jk]['label'][:10]:>10s}"
        header += f"  {'Claims':>6s}  {'Rnds':>4s}"
        print(header)
        print(f"  {'-' * (w - 4)}")

        for model in sorted(models.keys(), key=lambda m: -models[m].get("score", -1)):
            m = models[model]
            if m.get("score", -1) < 0:
                print(f"  {model:25s}  {'ERROR':>8s}")
                continue

            line = (
                f"  {model:25s}  {m['score']:7.1%}  "
                f"±{m.get('score_std', 0):.1%}  "
                f"{m['hallucination_rate']:5.1%}"
            )
            if multi:
                line += f"  {m.get('inter_judge_agreement', 0):5.0%}"
                for jk in JUDGE_CONFIGS:
                    pj = m.get("per_judge", {}).get(jk)
                    if pj:
                        line += f"  {pj['mean']:9.1%}"
                    else:
                        line += f"  {'---':>10s}"
            line += f"  {m['total_claims']:6d}  {m['num_rounds']:4d}"
            print(line)


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Judge Hallucination Evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full 3-judge panel, 3 rounds
  python evaluate_hallucination.py --rounds 3 --judges all

  # Single Gemini judge, 1 round (fast)
  python evaluate_hallucination.py --rounds 1 --judges gemini

  # Two judges
  python evaluate_hallucination.py --rounds 3 --judges gemini gpt
        """,
    )
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--start-round", type=int, default=1,
                        help="Starting round (e.g. 2 to skip R1)")
    parser.add_argument(
        "--judges", nargs="+", default=["all"],
        help="Judge keys: gemini, gpt, claude, or 'all' for 3-judge panel",
    )
    parser.add_argument("--max-claims", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=15)
    parser.add_argument("--max-workers", type=int, default=5)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--output", "-o", type=str,
        default="golden_outputs/hallucination_results.json",
    )
    parser.add_argument(
        "--golden", nargs="+", default=None,
        help="Only evaluate specific golden datasets (e.g. golden_d golden_e golden_f)",
    )
    parser.add_argument(
        "--models", nargs="+", default=None,
        help="Only evaluate specific model labels (e.g. gpt-5.4 claude-opus-4.6)",
    )
    parser.add_argument(
        "--merge", action="store_true",
        help="Merge results into existing output file instead of overwriting",
    )
    parser.add_argument(
        "--incremental", action="store_true",
        help="Skip model/dataset combos that already have enough rounds in the output file",
    )
    args = parser.parse_args()

    if "all" in args.judges:
        judge_keys = list(JUDGE_CONFIGS.keys())
    else:
        judge_keys = args.judges

    multi = len(judge_keys) > 1
    judge_labels = ", ".join(JUDGE_CONFIGS[jk]["label"] for jk in judge_keys)
    mode = "Multi-Judge Panel" if multi else "Single Judge"
    print(f"Running {mode}: {judge_labels}")
    print(f"  rounds={args.rounds}, max_claims={args.max_claims}, "
          f"batch_size={args.batch_size}, workers={args.max_workers}")
    if multi:
        print(f"  Aggregation: Majority Vote")
    if args.golden:
        print(f"  Golden filter: {args.golden}")
    if args.models:
        print(f"  Model filter: {args.models}")
    if args.incremental:
        print(f"  Incremental: skipping already-evaluated combos in {args.output}")
    print()

    aggregated = evaluate_all(
        num_rounds=args.rounds,
        judge_keys=judge_keys,
        max_claims=args.max_claims,
        batch_size=args.batch_size,
        max_workers=args.max_workers,
        verbose=args.verbose,
        golden_filter=args.golden,
        start_round=args.start_round,
        model_filter=args.models,
        existing_results_path=args.output if args.incremental else None,
    )

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    if (args.merge or args.incremental) and os.path.isfile(args.output):
        with open(args.output) as f:
            existing = json.load(f)
        for gn, models in aggregated.items():
            if gn not in existing:
                existing[gn] = {}
            existing[gn].update(models)
        aggregated = existing
    with open(args.output, "w") as f:
        json.dump(aggregated, f, indent=2)
    print(f"\nResults saved to: {args.output}")

    print_summary(aggregated, multi=multi)


if __name__ == "__main__":
    main()
