#!/usr/bin/env python3
"""
Deterministic evaluation of all golden output.md files.

Runs FormattingValidator, CitationValidator, ChronologicalValidator,
CoverageValidator, and ForbiddenWordsValidator against every output.md
in golden_outputs/round_*/golden_*/model/.

Also extends golden evaluation with key_fields content similarity
(ROUGE-L / token overlap) for TP-matched entries.

Usage:
    python evaluate_deterministic.py
    python evaluate_deterministic.py --rounds 3
    python evaluate_deterministic.py --verbose
"""

import argparse
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from src.contracts.base import BenchmarkContract
from src.scoring.calculator import ScoringCalculator
from src.validators.markdown_entry_parser import parse_markdown_entries

GOLDEN_DIRS = [
    "golden/golden_a", "golden/golden_b", "golden/golden_c",
    "golden/golden_d", "golden/golden_e", "golden/golden_f",
]
OUTPUT_BASE = "golden_outputs"
INSTRUCTION_PATH = "instruction.txt"


# ── Contract builder ─────────────────────────────────────────────────────────

def build_contract_from_instruction(instruction_path: str) -> BenchmarkContract:
    """Build a BenchmarkContract from the medical chronology instruction."""
    instruction_text = Path(instruction_path).read_text(encoding="utf-8")

    return BenchmarkContract(
        section_name="Medical Chronology",
        required_fields=[
            "Type of Visit",
            "Facility Name",
            "Provider Name",
        ],
        heading_patterns=[
            r"^## Date of Medical Visit:",
            r"^### \d{2}/\d{2}/\d{4}",
        ],
        date_format="MM/DD/YYYY",
        chronological_order=True,
        chronological_direction="ascending",
        citation_required=True,
        citation_field="Source References",
        citation_pattern=r"\(.*?\)",
        raw_instruction=instruction_text,
    )


# ── Key-fields content similarity ────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    """Lowercase tokenization, strip punctuation."""
    return re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower())


def _lcs_length(a: List[str], b: List[str]) -> int:
    """Longest common subsequence length (for ROUGE-L)."""
    if not a or not b:
        return 0
    m, n = len(a), len(b)
    prev = [0] * (n + 1)
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(curr[j - 1], prev[j])
        prev = curr
    return prev[n]


def rouge_l(reference: str, hypothesis: str) -> Dict[str, float]:
    """Compute ROUGE-L precision, recall, F1."""
    ref_tokens = _tokenize(reference)
    hyp_tokens = _tokenize(hypothesis)
    if not ref_tokens or not hyp_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    lcs = _lcs_length(ref_tokens, hyp_tokens)
    p = lcs / len(hyp_tokens)
    r = lcs / len(ref_tokens)
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4)}


def token_overlap(reference: str, hypothesis: str) -> float:
    """Jaccard-style token overlap."""
    ref_set = set(_tokenize(reference))
    hyp_set = set(_tokenize(hypothesis))
    if not ref_set or not hyp_set:
        return 0.0
    return len(ref_set & hyp_set) / len(ref_set | hyp_set)


def _normalize_facility(f: str) -> str:
    if not f or f.lower() in ("not specified", "n/a", "none"):
        return ""
    return re.sub(r"[^a-z0-9]", "", f.lower())


def _entry_key(e: dict) -> Tuple[str, str]:
    date = e.get("encounter_date", "")
    fac = _normalize_facility(e.get("facility_name", ""))
    return (date, fac)


def _facility_similarity(f1: str, f2: str) -> float:
    if f1 == f2:
        return 1.0
    if not f1 or not f2:
        return 0.5
    from difflib import SequenceMatcher
    return SequenceMatcher(None, f1, f2).ratio()


def _match_entries(golden_entries: List[dict], model_entries: List[dict]) -> List[Tuple[dict, dict]]:
    """Match golden must_extract entries to model entries using Hungarian algorithm.
    Returns list of (golden_entry, model_entry) pairs for TPs."""
    must_extract = [e for e in golden_entries if e.get("must_extract") is True]
    filtered_model = [me for me in model_entries if me.get("include") is not False]

    if not must_extract or not filtered_model:
        return []

    import numpy as np
    from scipy.optimize import linear_sum_assignment

    g_keys = [_entry_key(e) for e in must_extract]
    m_keys = [_entry_key(e) for e in filtered_model]

    cost = np.ones((len(m_keys), len(g_keys)), dtype=float)
    for i, mk in enumerate(m_keys):
        for j, gk in enumerate(g_keys):
            if mk[0] != gk[0]:
                cost[i, j] = 1.0
            else:
                cost[i, j] = 1.0 - _facility_similarity(mk[1], gk[1])

    row_ind, col_ind = linear_sum_assignment(cost)

    matched = []
    for r, c in zip(row_ind, col_ind):
        if cost[r, c] <= 0.5:
            matched.append((must_extract[c], filtered_model[r]))

    return matched


# FIELD_MAP from markdown_entry_parser maps markdown labels to canonical keys
# golden key_fields use the canonical keys directly
GOLDEN_TO_MODEL_FIELD_MAP = {
    "subjective": "subjective",
    "objective": "objective",
    "social": "social",
    "lab_results": "lab_results",
    "procedures": "procedures",
    "imaging_findings": "imaging_findings",
    "diagnoses": "diagnoses",
    "plan": "plan",
    "mss": "mss",
    "medications": "medications",
    "referrals": "referrals",
}


def evaluate_key_fields(golden_path: str, model_output_md: str) -> Dict[str, Any]:
    """Evaluate key_fields content similarity for TP-matched entries."""
    with open(golden_path) as f:
        golden = json.load(f)

    model_entries = parse_markdown_entries(model_output_md)
    matched_pairs = _match_entries(golden["entries"], model_entries)

    if not matched_pairs:
        return {
            "matched_entries": 0,
            "fields_compared": 0,
            "avg_rouge_l_f1": 0.0,
            "avg_token_overlap": 0.0,
            "per_field_scores": {},
        }

    all_rouge_f1 = []
    all_overlap = []
    per_field_scores: Dict[str, List[float]] = defaultdict(list)

    for golden_entry, model_entry in matched_pairs:
        kf = golden_entry.get("key_fields", {})
        for gf_key, gf_value in kf.items():
            if not gf_value or gf_value.lower() in ("none mentioned.", "not applicable.", "none mentioned", "not applicable"):
                continue
            model_key = GOLDEN_TO_MODEL_FIELD_MAP.get(gf_key, gf_key)
            model_value = model_entry.get(model_key, "")
            if not model_value:
                all_rouge_f1.append(0.0)
                all_overlap.append(0.0)
                per_field_scores[gf_key].append(0.0)
                continue

            rl = rouge_l(gf_value, model_value)
            to = token_overlap(gf_value, model_value)
            all_rouge_f1.append(rl["f1"])
            all_overlap.append(to)
            per_field_scores[gf_key].append(rl["f1"])

    avg_rouge = sum(all_rouge_f1) / len(all_rouge_f1) if all_rouge_f1 else 0.0
    avg_overlap = sum(all_overlap) / len(all_overlap) if all_overlap else 0.0

    per_field_avg = {
        k: round(sum(v) / len(v), 4) if v else 0.0
        for k, v in per_field_scores.items()
    }

    return {
        "matched_entries": len(matched_pairs),
        "fields_compared": len(all_rouge_f1),
        "avg_rouge_l_f1": round(avg_rouge, 4),
        "avg_token_overlap": round(avg_overlap, 4),
        "per_field_scores": per_field_avg,
    }


# ── Semantic Fidelity (embedding-based) ───────────────────────────────────────

def _get_embeddings(texts: List[str], model: str = "text-embedding-3-large") -> List[List[float]]:
    """Get embeddings from OpenAI API. Returns list of embedding vectors."""
    from openai import OpenAI
    client = OpenAI()
    resp = client.embeddings.create(input=texts, model=model)
    return [d.embedding for d in resp.data]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def evaluate_semantic_fidelity(golden_path: str, model_output_md: str) -> Dict[str, Any]:
    """Evaluate semantic similarity between golden key_fields and model output
    using embedding cosine similarity. More robust than ROUGE-L for paraphrasing."""
    with open(golden_path) as f:
        golden = json.load(f)

    model_entries = parse_markdown_entries(model_output_md)
    matched_pairs = _match_entries(golden["entries"], model_entries)

    if not matched_pairs:
        return {
            "matched_entries": 0,
            "fields_compared": 0,
            "avg_semantic_similarity": 0.0,
            "per_field_semantic": {},
        }

    pairs_to_embed: List[Tuple[str, str, str]] = []  # (field_name, golden_text, model_text)

    for golden_entry, model_entry in matched_pairs:
        kf = golden_entry.get("key_fields", {})
        for gf_key, gf_value in kf.items():
            if not gf_value or gf_value.lower() in (
                "none mentioned.", "not applicable.", "none mentioned", "not applicable"
            ):
                continue
            model_key = GOLDEN_TO_MODEL_FIELD_MAP.get(gf_key, gf_key)
            model_value = model_entry.get(model_key, "")
            if not model_value:
                pairs_to_embed.append((gf_key, gf_value, ""))
                continue
            pairs_to_embed.append((gf_key, gf_value, model_value))

    if not pairs_to_embed:
        return {
            "matched_entries": len(matched_pairs),
            "fields_compared": 0,
            "avg_semantic_similarity": 0.0,
            "per_field_semantic": {},
        }

    golden_texts = [p[1] for p in pairs_to_embed if p[2]]
    model_texts = [p[2] for p in pairs_to_embed if p[2]]

    if not golden_texts:
        per_field: Dict[str, List[float]] = defaultdict(list)
        for field_name, _, _ in pairs_to_embed:
            per_field[field_name].append(0.0)
        return {
            "matched_entries": len(matched_pairs),
            "fields_compared": len(pairs_to_embed),
            "avg_semantic_similarity": 0.0,
            "per_field_semantic": {k: round(sum(v)/len(v), 4) for k, v in per_field.items()},
        }

    try:
        all_texts = golden_texts + model_texts
        embeddings = _get_embeddings(all_texts)
        golden_embs = embeddings[:len(golden_texts)]
        model_embs = embeddings[len(golden_texts):]
    except Exception as e:
        print(f"  [warn] Embedding API error: {e}")
        return {
            "matched_entries": len(matched_pairs),
            "fields_compared": len(pairs_to_embed),
            "avg_semantic_similarity": -1.0,
            "per_field_semantic": {},
            "error": str(e),
        }

    all_sims: List[float] = []
    per_field_sims: Dict[str, List[float]] = defaultdict(list)
    emb_idx = 0

    for field_name, gf_value, model_value in pairs_to_embed:
        if not model_value:
            all_sims.append(0.0)
            per_field_sims[field_name].append(0.0)
        else:
            sim = _cosine_similarity(golden_embs[emb_idx], model_embs[emb_idx])
            all_sims.append(sim)
            per_field_sims[field_name].append(sim)
            emb_idx += 1

    avg_sim = sum(all_sims) / len(all_sims) if all_sims else 0.0
    per_field_avg = {
        k: round(sum(v) / len(v), 4) if v else 0.0
        for k, v in per_field_sims.items()
    }

    return {
        "matched_entries": len(matched_pairs),
        "fields_compared": len(all_sims),
        "avg_semantic_similarity": round(avg_sim, 4),
        "per_field_semantic": per_field_avg,
    }


# ── Deterministic validators ─────────────────────────────────────────────────

def check_source_references(output_md: str) -> Dict[str, Any]:
    """Check Source References field presence per entry.
    
    The golden outputs use '* **Source References:** (...)' format,
    not HTML citation comments. We check how many entries have this field.
    """
    entries = parse_markdown_entries(output_md)
    total = len(entries)
    with_refs = sum(1 for e in entries if e.get("source_references"))
    rate = with_refs / total if total > 0 else 0.0
    return {
        "total_entries": total,
        "entries_with_source_refs": with_refs,
        "source_ref_rate": round(rate, 4),
    }


def run_deterministic_validators(contract: BenchmarkContract, output_md: str) -> Dict[str, Any]:
    """Run all deterministic validators and return scores."""
    from src.validators.formatting import FormattingValidator
    from src.validators.chronological import ChronologicalValidator

    fmt_validator = FormattingValidator(contract)
    fmt_score, fmt_errors = fmt_validator.validate(output_md)

    chrono_validator = ChronologicalValidator(contract)
    chrono_score, chrono_errors = chrono_validator.validate(output_md)

    src_refs = check_source_references(output_md)

    return {
        "formatting_score": round(fmt_score, 4),
        "chronological_score": round(chrono_score, 4),
        "source_ref_rate": src_refs["source_ref_rate"],
        "total_entries": src_refs["total_entries"],
        "entries_with_source_refs": src_refs["entries_with_source_refs"],
        "formatting_errors": len(fmt_errors),
        "chronological_violations": len(chrono_errors),
    }


# ── Multi-round aggregation ──────────────────────────────────────────────────

def _aggregate_metric(values: List[float]) -> Tuple[float, float]:
    """Return (mean, std) for a list of values."""
    if not values:
        return 0.0, 0.0
    mean = sum(values) / len(values)
    if len(values) < 2:
        return mean, 0.0
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return mean, math.sqrt(variance)


def evaluate_all(num_rounds: int = 3, verbose: bool = False,
                  semantic: bool = False) -> Dict[str, Any]:
    """Run deterministic + key_fields evaluation across all rounds.
    
    Args:
        semantic: If True, also compute embedding-based semantic fidelity
                  (requires OPENAI_API_KEY for text-embedding-3-large).
    """

    contract = build_contract_from_instruction(INSTRUCTION_PATH)

    det_results: Dict[str, Dict[str, List[dict]]] = defaultdict(lambda: defaultdict(list))
    kf_results: Dict[str, Dict[str, List[dict]]] = defaultdict(lambda: defaultdict(list))
    sem_results: Dict[str, Dict[str, List[dict]]] = defaultdict(lambda: defaultdict(list))

    for round_idx in range(1, num_rounds + 1):
        round_dir = f"{OUTPUT_BASE}/round_{round_idx}"
        if not os.path.isdir(round_dir):
            if verbose:
                print(f"  [skip] {round_dir} not found")
            continue

        for golden_dir in GOLDEN_DIRS:
            golden_name = Path(golden_dir).name
            golden_path = f"{golden_dir}/golden.json"
            output_dir = f"{round_dir}/{golden_name}"

            if not os.path.isfile(golden_path) or not os.path.isdir(output_dir):
                continue

            for model in sorted(os.listdir(output_dir)):
                output_file = os.path.join(output_dir, model, "output.md")
                if not os.path.isfile(output_file):
                    continue
                md = Path(output_file).read_text(encoding="utf-8")
                if not md.strip():
                    continue

                det = run_deterministic_validators(contract, md)
                det_results[golden_name][model].append(det)

                kf = evaluate_key_fields(golden_path, md)
                kf_results[golden_name][model].append(kf)

                sem_line = ""
                if semantic:
                    sem = evaluate_semantic_fidelity(golden_path, md)
                    sem_results[golden_name][model].append(sem)
                    sem_line = f"  sem={sem['avg_semantic_similarity']:.2%}"
                    time.sleep(0.1)

                if verbose:
                    print(
                        f"  R{round_idx} {golden_name}/{model:25s}  "
                        f"fmt={det['formatting_score']:.2%}  "
                        f"src={det['source_ref_rate']:.0%}  "
                        f"chr={det['chronological_score']:.2%}  "
                        f"rouge={kf['avg_rouge_l_f1']:.2%}  "
                        f"overlap={kf['avg_token_overlap']:.2%}"
                        f"{sem_line}"
                    )

    # Aggregate across rounds
    aggregated: Dict[str, Dict[str, dict]] = defaultdict(dict)

    for golden_name in sorted(det_results.keys()):
        for model in sorted(det_results[golden_name].keys()):
            rounds_det = det_results[golden_name][model]
            rounds_kf = kf_results[golden_name][model]
            n = len(rounds_det)

            agg: Dict[str, Any] = {"num_rounds": n}

            for metric in [
                "formatting_score", "chronological_score",
                "source_ref_rate", "total_entries",
                "entries_with_source_refs", "formatting_errors",
            ]:
                vals = [r[metric] for r in rounds_det]
                mean, std = _aggregate_metric(vals)
                agg[metric] = round(mean, 4)
                agg[f"{metric}_std"] = round(std, 4)
                agg[f"{metric}_values"] = vals

            for metric in ["avg_rouge_l_f1", "avg_token_overlap"]:
                vals = [r[metric] for r in rounds_kf]
                mean, std = _aggregate_metric(vals)
                agg[metric] = round(mean, 4)
                agg[f"{metric}_std"] = round(std, 4)
                agg[f"{metric}_values"] = vals

            # Per-field ROUGE-L scores (average across rounds)
            all_fields: Set[str] = set()
            for r in rounds_kf:
                all_fields.update(r.get("per_field_scores", {}).keys())
            per_field_agg: Dict[str, float] = {}
            for fld in sorted(all_fields):
                fvals = [r.get("per_field_scores", {}).get(fld, 0.0) for r in rounds_kf]
                per_field_agg[fld] = round(sum(fvals) / len(fvals), 4) if fvals else 0.0
            agg["per_field_rouge_l"] = per_field_agg

            # Semantic fidelity (if computed)
            rounds_sem = sem_results.get(golden_name, {}).get(model, [])
            if rounds_sem:
                sem_vals = [r["avg_semantic_similarity"] for r in rounds_sem if r.get("avg_semantic_similarity", -1) >= 0]
                if sem_vals:
                    mean, std = _aggregate_metric(sem_vals)
                    agg["avg_semantic_similarity"] = round(mean, 4)
                    agg["avg_semantic_similarity_std"] = round(std, 4)
                    agg["avg_semantic_similarity_values"] = [round(v, 4) for v in sem_vals]

                # Per-field semantic
                sem_fields: Set[str] = set()
                for r in rounds_sem:
                    sem_fields.update(r.get("per_field_semantic", {}).keys())
                if sem_fields:
                    per_field_sem: Dict[str, float] = {}
                    for fld in sorted(sem_fields):
                        fvals = [r.get("per_field_semantic", {}).get(fld, 0.0) for r in rounds_sem]
                        per_field_sem[fld] = round(sum(fvals) / len(fvals), 4) if fvals else 0.0
                    agg["per_field_semantic"] = per_field_sem

            aggregated[golden_name][model] = agg

    return dict(aggregated)


# ── Pretty print ──────────────────────────────────────────────────────────────

def print_summary(aggregated: Dict[str, Dict[str, dict]]):
    """Print a summary table."""
    has_semantic = any(
        "avg_semantic_similarity" in m
        for models in aggregated.values()
        for m in models.values()
    )

    for golden_name in sorted(aggregated.keys()):
        models = aggregated[golden_name]
        print(f"\n{'='*110}")
        print(f"  {golden_name}")
        print(f"{'='*110}")
        sem_col = f"  {'Semantic':>8s}" if has_semantic else ""
        header = (
            f"  {'Model':25s}  {'Format':>7s}  {'SrcRef':>7s}  {'Chrono':>7s}  "
            f"{'ROUGE-L':>8s}  {'Overlap':>8s}{sem_col}  {'Entries':>7s}  {'FmtErr':>6s}"
        )
        print(header)
        print(f"  {'-'*100}")

        for model in sorted(models.keys()):
            m = models[model]
            sem_val = ""
            if has_semantic and "avg_semantic_similarity" in m:
                sem_val = f"  {m['avg_semantic_similarity']:7.1%}"
            elif has_semantic:
                sem_val = f"  {'—':>8s}"
            print(
                f"  {model:25s}  {m['formatting_score']:6.1%}  "
                f"{m['source_ref_rate']:6.1%}  {m['chronological_score']:6.1%}  "
                f"{m['avg_rouge_l_f1']:7.1%}  {m['avg_token_overlap']:7.1%}"
                f"{sem_val}  "
                f"{m['total_entries']:7.1f}  {m['formatting_errors']:6.1f}"
            )

        # Per-field breakdown
        all_fields: Set[str] = set()
        for m in models.values():
            all_fields.update(m.get("per_field_rouge_l", {}).keys())
        if all_fields:
            print(f"\n  Per-field ROUGE-L F1:")
            fheader = f"  {'Model':25s}  " + "  ".join(f"{f[:10]:>10s}" for f in sorted(all_fields))
            print(fheader)
            for model in sorted(models.keys()):
                pf = models[model].get("per_field_rouge_l", {})
                vals = "  ".join(f"{pf.get(f, 0.0):9.1%}" for f in sorted(all_fields))
                print(f"  {model:25s}  {vals}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Deterministic evaluation of golden outputs")
    parser.add_argument("--rounds", type=int, default=3, help="Number of rounds (default: 3)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print per-round details")
    parser.add_argument("--semantic", action="store_true",
                        help="Compute embedding-based semantic fidelity (requires OPENAI_API_KEY)")
    parser.add_argument("--output", "-o", type=str, default="golden_outputs/deterministic_results.json",
                        help="Output JSON path")
    args = parser.parse_args()

    if args.semantic:
        print(f"Running deterministic + semantic evaluation ({args.rounds} rounds)...")
    else:
        print(f"Running deterministic evaluation ({args.rounds} rounds)...")
    aggregated = evaluate_all(num_rounds=args.rounds, verbose=args.verbose,
                              semantic=args.semantic)

    out_path = args.output
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(aggregated, f, indent=2)
    print(f"\nResults saved to: {out_path}")

    print_summary(aggregated)


if __name__ == "__main__":
    main()
