#!/usr/bin/env python3
"""
Build consensus golden entries from multiple model outputs.

Instead of using a single model's output as ground truth, this script
parses outputs from ALL available models and builds consensus:
  - 2+ models extracted it → must_extract (high confidence)
  - 1 model extracted it   → may_extract  (ambiguous)

This eliminates bias toward any single model family.

Usage:
    # Build consensus for all 3 sources
    python build_consensus_golden.py

    # Build for a specific source, with custom threshold
    python build_consensus_golden.py --source a --threshold 2

    # Dry run (show consensus without saving)
    python build_consensus_golden.py --dry-run
"""

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent))
from src.validators.markdown_entry_parser import parse_markdown_entries


SOURCES = {
    "a": {
        "output_dir": "outputs/mc_source_a_small_v2",
        "golden_dir": "golden/golden_a",
        "style": "dde",
    },
    "b": {
        "output_dir": "outputs/mc_source_b_small_v2",
        "golden_dir": "golden/golden_b",
        "style": "clinical_note",
    },
    "c": {
        "output_dir": "outputs/mc_source_c_small_v2",
        "golden_dir": "golden/golden_c",
        "style": "mixed",
    },
}

# Models to exclude from consensus (e.g., known bad outputs)
EXCLUDE_MODELS = set()


def _normalize_facility(f: str) -> str:
    if not f or f.lower() in ("not specified", "n/a", "none"):
        return ""
    return re.sub(r"[^a-z0-9]", "", f.lower())


def _normalize_date(d: str) -> str:
    """Normalize date to YYYY-MM-DD."""
    d = d.strip()
    if re.match(r"\d{4}-\d{2}-\d{2}", d):
        return d
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", d)
    if m:
        return f"{m.group(3)}-{m.group(1).zfill(2)}-{m.group(2).zfill(2)}"
    return d


def parse_model_outputs(output_dir: str) -> Dict[str, List[Dict]]:
    """Parse all model outputs in a directory. Returns {model_name: [entries]}."""
    results = {}
    output_path = Path(output_dir)
    if not output_path.exists():
        print(f"  Warning: {output_dir} not found")
        return results

    for model_dir in sorted(output_path.iterdir()):
        if not model_dir.is_dir():
            continue
        model_name = model_dir.name
        if model_name in EXCLUDE_MODELS:
            continue

        output_file = model_dir / "output.md"
        if not output_file.exists():
            continue

        md_text = output_file.read_text(encoding="utf-8")
        if not md_text.strip():
            print(f"  Skipping {model_name} (empty output)")
            continue

        entries = parse_markdown_entries(md_text)
        parsed = []
        for e in entries:
            if e.get("include") is False:
                continue
            parsed.append({
                "encounter_date": _normalize_date(e.get("encounter_date", "")),
                "facility_name": e.get("facility_name", "Not specified"),
                "provider_name": e.get("provider_name", "Not specified"),
                "visit_type": e.get("visit_type", ""),
                "key_fields": {
                    k: v for k, v in e.items()
                    if k not in ("include", "exclude_reason", "encounter_date",
                                 "date_display", "facility_name", "provider_name",
                                 "visit_type", "source_references")
                    and v and isinstance(v, str)
                    and v.strip().lower() not in ("not specified", "n/a", "none", "")
                },
            })
        results[model_name] = parsed
        print(f"  {model_name}: {len(parsed)} entries")

    return results


def build_consensus(
    model_outputs: Dict[str, List[Dict]],
    must_threshold: int = 2,
) -> Tuple[List[Dict], List[Dict]]:
    """Build consensus entries from multiple model outputs.
    
    Returns (must_extract_entries, may_extract_entries).
    
    An entry is identified by (date, normalized_facility). If facility differs
    across models, we use the most common non-empty facility name.
    """
    # Group entries by date
    date_entries = defaultdict(list)
    for model_name, entries in model_outputs.items():
        seen_dates = set()
        for e in entries:
            date = e["encounter_date"]
            if date in seen_dates:
                continue
            seen_dates.add(date)
            date_entries[date].append({
                "model": model_name,
                **e,
            })

    total_models = len(model_outputs)
    must_extract = []
    may_extract = []

    for date in sorted(date_entries.keys()):
        entries_for_date = date_entries[date]
        model_count = len(set(e["model"] for e in entries_for_date))

        # Pick best facility name (most common non-empty)
        facility_counts = defaultdict(int)
        for e in entries_for_date:
            fac = e["facility_name"]
            if fac and fac.lower() not in ("not specified", "n/a", "none"):
                facility_counts[fac] += 1
        best_facility = max(facility_counts, key=facility_counts.get) if facility_counts else "Not specified"

        # Pick best provider name
        provider_counts = defaultdict(int)
        for e in entries_for_date:
            prov = e["provider_name"]
            if prov and prov.lower() not in ("not specified", "n/a", "none"):
                provider_counts[prov] += 1
        best_provider = max(provider_counts, key=provider_counts.get) if provider_counts else "Not specified"

        # Pick best visit type
        vt_counts = defaultdict(int)
        for e in entries_for_date:
            vt = e.get("visit_type", "")
            if vt:
                vt_counts[vt] += 1
        best_visit_type = max(vt_counts, key=vt_counts.get) if vt_counts else ""

        # Merge key_fields from all models (union)
        merged_fields = {}
        for e in entries_for_date:
            for k, v in e.get("key_fields", {}).items():
                if k not in merged_fields or len(v) > len(merged_fields[k]):
                    merged_fields[k] = v

        entry = {
            "encounter_date": date,
            "facility_name": best_facility,
            "provider_name": best_provider,
            "visit_type": best_visit_type,
            "key_fields": merged_fields,
            "consensus_count": model_count,
            "consensus_models": sorted(set(e["model"] for e in entries_for_date)),
        }

        if model_count >= must_threshold:
            must_extract.append(entry)
        else:
            may_extract.append(entry)

    return must_extract, may_extract


def build_golden_json(
    must_entries: List[Dict],
    may_entries: List[Dict],
    source_info: Dict,
    total_models: int,
) -> Dict:
    """Build golden.json structure from consensus entries."""
    from datetime import datetime, timezone

    entries = []
    idx = 0

    for e in must_entries:
        entries.append({
            "index": idx,
            "encounter_date": e["encounter_date"],
            "facility_name": e["facility_name"],
            "provider_name": e["provider_name"],
            "visit_type": e["visit_type"],
            "must_extract": True,
            "key_fields": e["key_fields"],
            "consensus_count": e["consensus_count"],
            "consensus_models": e["consensus_models"],
        })
        idx += 1

    for e in may_entries:
        entries.append({
            "index": idx,
            "encounter_date": e["encounter_date"],
            "facility_name": e["facility_name"],
            "provider_name": e["provider_name"],
            "visit_type": e["visit_type"],
            "must_extract": "may_extract",
            "key_fields": e.get("key_fields", {}),
            "consensus_count": e["consensus_count"],
            "consensus_models": e["consensus_models"],
        })
        idx += 1

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "method": "multi-model-consensus",
        "source_outputs": source_info["output_dir"],
        "consensus_models_used": total_models,
        "consensus_threshold": 2,
        "style": source_info["style"],
        "source_file": "synthetic_source.txt",
        "total_must_extract": len(must_entries),
        "total_may_extract": len(may_entries),
        "entries": entries,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build consensus golden entries")
    parser.add_argument("--source", "-s", choices=["a", "b", "c", "all"], default="all")
    parser.add_argument("--threshold", "-t", type=int, default=2,
                        help="Min models to agree for must_extract (default: 2)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sources_to_process = list(SOURCES.keys()) if args.source == "all" else [args.source]

    for src_key in sources_to_process:
        src = SOURCES[src_key]
        print(f"\n{'='*60}")
        print(f"  Building consensus for source {src_key} ({src['style']})")
        print(f"{'='*60}")

        # Parse all model outputs
        model_outputs = parse_model_outputs(src["output_dir"])
        if not model_outputs:
            print(f"  No model outputs found, skipping")
            continue

        total_models = len(model_outputs)
        print(f"\n  Total models: {total_models}")

        # Build consensus
        must, may = build_consensus(model_outputs, must_threshold=args.threshold)
        print(f"\n  Consensus results (threshold={args.threshold}/{total_models}):")
        print(f"    must_extract: {len(must)} entries")
        for e in must:
            models_str = ", ".join(e["consensus_models"])
            print(f"      [{e['consensus_count']}/{total_models}] {e['encounter_date']} | {e['facility_name']} | {e['visit_type'][:50]}")
        print(f"    may_extract:  {len(may)} entries")
        for e in may:
            models_str = ", ".join(e["consensus_models"])
            print(f"      [{e['consensus_count']}/{total_models}] {e['encounter_date']} | {e['facility_name']} ({models_str})")

        if args.dry_run:
            print(f"\n  [DRY RUN] Would save to {src['golden_dir']}/golden.json")
            continue

        # Build and save golden.json
        golden = build_golden_json(must, may, src, total_models)

        golden_dir = Path(src["golden_dir"])
        golden_dir.mkdir(parents=True, exist_ok=True)

        # Backup existing
        golden_path = golden_dir / "golden.json"
        if golden_path.exists():
            backup = golden_path.with_suffix(".json.pre_consensus")
            if not backup.exists():
                import shutil
                shutil.copy2(golden_path, backup)
                print(f"\n  Backed up existing golden.json → {backup.name}")

        with open(golden_path, "w") as f:
            json.dump(golden, f, indent=2)
        print(f"  Saved: {golden_path}")

        print(f"\n  Next: run synthesis with these consensus entries:")
        print(f"    python synthesize_golden.py --output CONSENSUS --out-dir {src['golden_dir']} --style {src['style']}")


if __name__ == "__main__":
    main()
