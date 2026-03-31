#!/usr/bin/env python3
"""
Synthesize Golden Dataset for Medical Chronology Benchmark.

Takes a real markdown output (ground truth) and reverse-synthesizes a
realistic source document using an LLM. The result is a (synthetic_source,
golden_entries) pair that enables precise Precision/Recall/F1 evaluation.

Usage:
    # From a single markdown output
    python synthesize_golden.py \
        --output outputs/mc_source_b_small_v2/gemini-2.5-pro/output.md \
        --out-dir golden/golden_b \
        --style dde

    # From multiple outputs, different styles
    python synthesize_golden.py \
        --output outputs/mc_source_a_small_v2/gemini-2.5-pro/output.md \
        --out-dir golden/golden_a \
        --style clinical_note

    # Validate only (check existing golden dataset)
    python synthesize_golden.py \
        --validate golden/golden_a/golden.json

Styles:
    dde            - Disability Determination Explanation summary
    clinical_note  - SOAP-style clinical notes
    mixed          - Mixed formats with OCR noise and admin records
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
load_dotenv(override=True)

# Reuse the markdown parser
sys.path.insert(0, str(Path(__file__).parent))
from src.validators.markdown_entry_parser import parse_markdown_entries, FIELD_MAP


# ── Synthesis Prompt ────────────────────────────────────────────────────────

SYNTHESIS_PROMPT = """You are a medical records simulator creating realistic source documents for a medical-legal benchmark.

## Your Task
Generate a raw medical record document that contains specific clinical encounters. A medical-legal analyst will use this document to extract a medical chronology. The document must be realistic and challenging — not a clean summary.

## MANDATORY RULES

### Rule 1: Every Date Must Appear
These dates MUST appear in the document (in any date format):
{date_checklist}

### Rule 2: Paraphrase Everything
You will receive structured encounter data. You MUST rewrite ALL clinical content using different words:
- Change sentence structure (active ↔ passive, combine/split sentences)
- Use different medical abbreviations (e.g., "BP 126/86" → "blood pressure was one-twenty-six over eighty-six")
- Reorder information within each encounter
- Embed clinical values in narrative prose, not bullet points
- NEVER copy phrases longer than 5 words from the input

### Rule 3: No Summaries or Answer Keys
- Do NOT include any "chronological summary" section that lists all encounters with dates
- Do NOT include any table of contents that reveals encounter dates
- The reader must find encounters by reading through the full document

### Rule 4: No Filler
- NEVER output lines of "..." or repeated placeholder text
- NEVER output "[BLANK PAGE]" or similar
- Every line must contain meaningful text (clinical notes, admin records, lab reports, consent forms, etc.)
- If you need more length, add: historical records, detailed lab reports with reference ranges, consent forms, demographic sheets, prior authorization forms, insurance correspondence

### Rule 5: Noise Must Be Non-Clinical
- Include {noise_count} non-clinical entries (billing, scheduling, insurance, records requests, prior authorizations, provider directory updates)
- These noise entries should have dates and facility names, but must NOT describe a clinical encounter (no chief complaint, no exam findings, no diagnoses, no treatment plan)
- Do NOT label them with "[ADMIN]" or "[NON-CLINICAL]"
- Include at least 5 dates that are NOT encounter dates (fax timestamps, referral dates, document received dates)
- CRITICAL: Do NOT invent any new clinical encounters beyond the {entry_count} listed in "Ground Truth Encounters". Every clinical visit in the document must correspond to one of the provided encounters. Noise is ONLY administrative/logistical content.

### Rule 6: Split Information Across Sections
- For at least 2 encounters, split the clinical information across different exhibits/sections
  (e.g., subjective in one section, lab results in another, imaging in a third)
- This forces the reader to synthesize information from multiple locations

## Document Style
{style_description}

## Realistic Artifacts to Include
- OCR-style typos: "rnedication", "0bjective", "dlagnosis", "1aboratory" (about 8-10 total)
- Page headers/footers with document IDs and page numbers on every page break
- Inconsistent date formats: MM/DD/YYYY, Month DD, YYYY, DD-Mon-YY, YYYY-MM-DD (mix them)
- Exhibit/section labels
- Fax headers, electronic signature blocks, timestamps

## Output Format
- Raw text only, NO markdown formatting
- Aim for approximately {target_length} characters of meaningful content
- Start with a header block (patient ID, claim number)
- Organize by exhibit/section

## Ground Truth Encounters
{entries_json}

## FINAL VERIFICATION
Before outputting, check:
✓ All {entry_count} encounter dates appear somewhere in the document
✓ The document contains EXACTLY {entry_count} clinical encounters — no more, no less
✓ No "chronological summary" or "table of contents" that lists all dates
✓ All clinical content is paraphrased (no verbatim copying)
✓ No filler lines ("...", blank pages)
✓ Noise entries are purely administrative (no clinical findings, no diagnoses)
✓ At least 2 encounters have information split across sections

Generate the document now. Output ONLY the raw text, no explanations."""


STYLE_DESCRIPTIONS = {
    "dde": "Disability Determination Explanation (DDE) — a government document organized by exhibit number. Each exhibit is a narrative paragraph summarizing records from a specific provider. Clinical details are embedded in dense prose, not listed cleanly. Include: Section A (jurisdictional data), Section B (evidence list WITHOUT dates), Section C (claimant allegations), Section D (medical evidence — this is where encounters are embedded in narrative), Section E (consultative exam), Section F (RFC analysis referencing specific encounters). Add a Function Report section and a Third Party Report with overlapping but slightly different information.",
    "clinical_note": "Clinical Progress Notes from an EHR system. Each note has a header (Date, Provider, Facility) followed by SOAP sections. IMPORTANT: vary the format — some notes should be complete SOAP, some should be brief (just CC + Plan), some should have addendums added days later, one should be a nursing intake note with minimal structure. Include lab result printouts between clinical notes. Add at least one note that references a visit at a DIFFERENT facility. Include a medication reconciliation list and a problem list somewhere in the document.",
    "mixed": "Mixed-format medical record compilation from multiple sources with inconsistent formatting. Include: (1) raw clinical notes from different EHR systems with different formats, (2) scanned imaging reports, (3) a discharge summary, (4) insurance correspondence, (5) lab reports with full reference ranges. Each source should have a slightly different header format. Some sections should look OCR'd with more artifacts. Do NOT include any chronological summary or table of contents that reveals encounter dates.",
}

NOISE_COUNTS = {"dde": 6, "clinical_note": 5, "mixed": 8}
TARGET_LENGTHS = {"dde": 50000, "clinical_note": 60000, "mixed": 70000}


# ── Entry Extraction ────────────────────────────────────────────────────────

def extract_golden_entries(md_text: str) -> List[Dict[str, Any]]:
    """Parse markdown output into golden entries with must_extract flags."""
    parsed = parse_markdown_entries(md_text)
    golden = []
    for i, entry in enumerate(parsed):
        ge = {
            "index": i,
            "encounter_date": entry.get("encounter_date", ""),
            "facility_name": entry.get("facility_name", "Not specified"),
            "provider_name": entry.get("provider_name", "Not specified"),
            "visit_type": entry.get("visit_type", ""),
            "must_extract": True,
            "key_fields": {},
        }
        for k, v in entry.items():
            if k in ("include", "exclude_reason", "encounter_date", "date_display",
                      "facility_name", "provider_name", "visit_type", "source_references"):
                continue
            if v and isinstance(v, str) and v.strip().lower() not in ("not specified", "n/a", "none", ""):
                ge["key_fields"][k] = v
        golden.append(ge)
    return golden


# ── Synthesis ───────────────────────────────────────────────────────────────

def synthesize_source(entries: List[Dict[str, Any]], style: str, max_retries: int = 3) -> str:
    """Call LLM to reverse-synthesize a source document from golden entries.
    
    Retries if not all dates are found in the generated source.
    Keeps the best attempt (fewest missing dates).
    """
    style_desc = STYLE_DESCRIPTIONS[style]
    noise_count = NOISE_COUNTS[style]
    target_length = TARGET_LENGTHS[style]

    entries_for_prompt = []
    all_dates = []
    for e in entries:
        entry_info = {
            "date": e["encounter_date"],
            "facility": e["facility_name"],
            "provider": e["provider_name"],
            "visit_type": e["visit_type"],
        }
        entry_info.update(e.get("key_fields", {}))
        entries_for_prompt.append(entry_info)
        all_dates.append(e["encounter_date"])

    date_checklist = "\n".join(f"  - {d}" for d in all_dates)

    prompt = SYNTHESIS_PROMPT.format(
        style_description=style_desc,
        noise_count=noise_count,
        target_length=f"{target_length:,}",
        entries_json=json.dumps(entries_for_prompt, indent=2),
        date_checklist=date_checklist,
        entry_count=len(entries),
    )

    provider = os.environ.get("SYNTH_PROVIDER", "gemini")

    best_source = None
    best_missing_count = len(all_dates) + 1

    for attempt in range(max_retries + 1):
        if attempt > 0:
            print(f"  Retry {attempt}/{max_retries} — best so far has {best_missing_count} missing dates")

        if provider == "gemini":
            source = _call_gemini(prompt)
        elif provider == "genai":
            source = _call_genai(prompt)
        else:
            raise ValueError(f"Unknown SYNTH_PROVIDER: {provider}")

        missing = _check_dates_in_source(all_dates, source)
        if not missing:
            return source

        if len(missing) < best_missing_count:
            best_missing_count = len(missing)
            best_source = source
        print(f"  Warning: attempt {attempt + 1} missing {len(missing)} dates: {missing}")

    # Post-process: patch missing dates into the source
    if best_source and best_missing_count > 0:
        missing = _check_dates_in_source(all_dates, best_source)
        best_source = _patch_missing_dates(best_source, missing, entries)
        remaining = _check_dates_in_source(all_dates, best_source)
        if remaining:
            print(f"  After patching, still missing {len(remaining)}: {remaining}")
        else:
            print(f"  Patched {len(missing)} missing dates — now 100% coverage")
    else:
        print(f"  Proceeding with best attempt ({best_missing_count} missing dates)")
    return best_source


def _check_dates_in_source(dates: List[str], source: str) -> List[str]:
    """Return list of dates not found in source text."""
    missing = []
    for d in dates:
        parts = d.split("-")
        if len(parts) != 3:
            continue
        yyyy, mm, dd = parts
        formats = [
            f"{mm}/{dd}/{yyyy}",
            f"{int(mm)}/{int(dd)}/{yyyy}",
            f"{yyyy}-{mm}-{dd}",
        ]
        if not any(fmt in source for fmt in formats):
            missing.append(d)
    return missing


def _patch_missing_dates(source: str, missing_dates: List[str], entries: List[Dict]) -> str:
    """Insert missing encounter dates into the source as addendum notes."""
    entry_map = {e["encounter_date"]: e for e in entries}
    patches = []
    for d in missing_dates:
        entry = entry_map.get(d)
        if not entry:
            continue
        parts = d.split("-")
        yyyy, mm, dd = parts
        date_str = f"{int(mm)}/{int(dd)}/{yyyy}"
        facility = entry.get("facility_name", "Unknown Facility")
        visit_type = entry.get("visit_type", "Office Visit")
        provider = entry.get("provider_name", "")

        patch = f"\n\n--- ADDENDUM / LATE ENTRY ---\n"
        patch += f"Date of Service: {date_str}\n"
        if facility and facility != "Not specified":
            patch += f"Location: {facility}\n"
        if provider and provider != "Not specified":
            patch += f"Provider: {provider}\n"
        patch += f"Visit Type: {visit_type}\n"

        key_fields = entry.get("key_fields", {})
        if key_fields:
            patch += "Clinical Note:\n"
            for k, v in key_fields.items():
                label = k.replace("_", " ").title()
                patch += f"  {label}: {v}\n"
        patch += f"--- END ADDENDUM ---\n"
        patches.append(patch)

    if patches:
        insert_point = source.rfind("\n===")
        if insert_point == -1:
            insert_point = len(source) - 200
        source = source[:insert_point] + "\n".join(patches) + source[insert_point:]
    return source


def _extract_noise_dates(source: str, golden_dates: set) -> List[str]:
    """Extract dates from source that are NOT in the golden set (noise dates)."""
    from src.validators.markdown_entry_parser import _DATE_MMDDYYYY, _DATE_ISO

    found_dates = set()
    for m in _DATE_MMDDYYYY.finditer(source):
        mm, dd, yyyy = m.group(1), m.group(2), m.group(3)
        iso = f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"
        found_dates.add(iso)
    for m in _DATE_ISO.finditer(source):
        found_dates.add(m.group(0))

    noise = sorted(found_dates - golden_dates)
    return noise


ENCOUNTER_SCAN_PROMPT_TEMPLATE = (
    'You are a medical record analyst. Read the following source document and identify ALL segments '
    'that look like clinical encounters (visits with a healthcare provider where clinical findings, '
    'diagnoses, or treatment plans are documented).\n\n'
    'For each encounter-like segment, extract:\n'
    '- date (ISO format YYYY-MM-DD)\n'
    '- facility or provider name\n'
    '- brief description (1 sentence)\n\n'
    'Return ONLY a JSON array. If no encounters found, return [].\n'
    'Example: [{{"date": "2023-05-15", "facility": "Metro Clinic", "description": "Annual physical with BP and labs"}}]\n\n'
    'IMPORTANT: Only include segments that describe actual clinical encounters (with exam findings, '
    'diagnoses, or treatment). Do NOT include administrative entries (billing, scheduling, insurance, '
    'records requests, prior authorizations).\n\n'
    'Source document:\n{source_text}'
)


def _scan_for_extra_encounters(
    source: str,
    golden_dates: set,
    provider: str = None,
) -> List[Dict[str, Any]]:
    """Use LLM to scan synthetic source for encounter-like content not in golden entries.
    
    Returns list of {date, facility, description} for encounters that appear
    clinical but are NOT in the golden entry set — these become may_extract.
    """
    provider = provider or os.environ.get("SYNTH_PROVIDER", "gemini")
    prompt = ENCOUNTER_SCAN_PROMPT_TEMPLATE.format(source_text=source[:80000])

    if provider == "gemini":
        raw = _call_gemini(prompt)
    elif provider == "genai":
        raw = _call_genai(prompt)
    else:
        raw = _call_gemini(prompt)

    # Parse JSON from response
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```\w*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        encounters = json.loads(cleaned)
    except json.JSONDecodeError:
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if json_match:
            try:
                encounters = json.loads(json_match.group(0))
            except json.JSONDecodeError:
                print("  Warning: Could not parse encounter scan response")
                return []
        else:
            print("  Warning: No JSON found in encounter scan response")
            return []

    extras = []
    for enc in encounters:
        date = enc.get("date", "")
        if date in golden_dates:
            continue
        extras.append({
            "date": date,
            "facility": enc.get("facility", "Unknown"),
            "description": enc.get("description", ""),
        })

    return extras


def _call_gemini(prompt: str) -> str:
    """Call Gemini via the standard google-cloud-aiplatform SDK."""
    sys.path.insert(0, str(Path(__file__).parent))
    from llm import LLMClient
    from llm.base import LLMConfig

    model = os.environ.get("SYNTH_MODEL", "gemini-2.5-pro")
    config = LLMConfig(model=model, max_tokens=65000)
    client = LLMClient.create(
        provider_type="gemini",
        model=model,
        config=config,
        logs_dir=None,
    )
    import asyncio
    result = asyncio.run(client.generate(prompt))
    if hasattr(result, 'content'):
        return result.content
    return str(result)


def _call_genai(prompt: str) -> str:
    """Call via google-genai SDK (for Gemini 3+ preview models)."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GOOGLE_AI_STUDIO_API_KEY")
    client = genai.Client(api_key=api_key)
    model = os.environ.get("SYNTH_MODEL", "gemini-2.5-pro")

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=65000,
            temperature=0.8,
        ),
    )
    return response.text


# ── Validation ──────────────────────────────────────────────────────────────

def validate_golden(golden_path: str) -> Dict[str, Any]:
    """Validate that a synthetic source contains all expected entries."""
    with open(golden_path) as f:
        golden = json.load(f)

    source_path = Path(golden_path).parent / golden["source_file"]
    if not source_path.exists():
        return {"valid": False, "error": f"Source file not found: {source_path}"}

    source_text = source_path.read_text(encoding="utf-8")
    source_lower = source_text.lower()

    results = {"valid": True, "entries": [], "warnings": []}

    for entry in golden["entries"]:
        if entry.get("must_extract") is not True:
            continue

        date = entry["encounter_date"]
        facility = entry.get("facility_name", "")

        # Check date appears in source (try multiple formats)
        date_found = False
        if date:
            parts = date.split("-")
            if len(parts) == 3:
                yyyy, mm, dd = parts
                formats_to_check = [
                    f"{mm}/{dd}/{yyyy}",
                    f"{int(mm)}/{int(dd)}/{yyyy}",
                    f"{yyyy}-{mm}-{dd}",
                    date,
                ]
                for fmt in formats_to_check:
                    if fmt in source_text:
                        date_found = True
                        break

        # Check facility appears in source (fuzzy)
        facility_found = False
        if facility and facility.lower() not in ("not specified", "n/a"):
            facility_words = [w for w in facility.lower().split() if len(w) > 3]
            if facility_words:
                matches = sum(1 for w in facility_words if w in source_lower)
                facility_found = matches >= len(facility_words) * 0.6

        entry_result = {
            "encounter_date": date,
            "facility": facility,
            "date_found": date_found,
            "facility_found": facility_found,
        }
        results["entries"].append(entry_result)

        if not date_found:
            results["valid"] = False
            results["warnings"].append(f"Date {date} NOT found in source")
        if not facility_found and facility.lower() not in ("not specified", "n/a"):
            results["warnings"].append(f"Facility '{facility}' may not be in source (fuzzy check)")

    # Check noise entries exist
    noise_entries = [e for e in golden["entries"] if e.get("must_extract") is False]
    may_entries = [e for e in golden["entries"] if e.get("must_extract") == "may_extract"]
    if not noise_entries:
        results["warnings"].append("No noise entries defined — false inclusion testing won't work")

    found_count = sum(1 for e in results["entries"] if e["date_found"])
    total_must = len([e for e in golden["entries"] if e.get("must_extract") is True])
    results["summary"] = {
        "total_must_extract": total_must,
        "total_may_extract": len(may_entries),
        "dates_found_in_source": found_count,
        "noise_entries": len(noise_entries),
        "coverage": f"{found_count}/{total_must}",
    }

    return results


# ── Golden Evaluator ────────────────────────────────────────────────────────

def evaluate_against_golden(
    golden_path: str,
    model_output_md: str,
) -> Dict[str, Any]:
    """
    Evaluate a model's markdown output against a golden dataset.
    Returns Precision, Recall, F1, and False Inclusion Rate.
    
    Entry categories:
      - must_extract=True:         TP if found, FN if missed
      - must_extract="may_extract": absorbed silently (not FP, not FN)
      - must_extract=False:        FP if found (false inclusion)
    """
    with open(golden_path) as f:
        golden = json.load(f)

    must_extract = [e for e in golden["entries"] if e.get("must_extract") is True]
    may_extract = [e for e in golden["entries"] if e.get("must_extract") == "may_extract"]
    noise_entries = [e for e in golden["entries"] if e.get("must_extract") is False]

    model_entries = parse_markdown_entries(model_output_md)

    def _normalize_facility(f):
        if not f or f.lower() in ("not specified", "n/a", "none"):
            return ""
        return re.sub(r"[^a-z0-9]", "", f.lower())

    def _entry_key(e):
        date = e.get("encounter_date", "")
        fac = _normalize_facility(e.get("facility_name", ""))
        return (date, fac)

    model_keys_list = []
    for e in model_entries:
        if e.get("include") is False:
            continue
        model_keys_list.append((_entry_key(e), e))

    def _facility_similarity(f1, f2):
        """Similarity between two normalized facility names (0.0–1.0)."""
        if f1 == f2:
            return 1.0
        if not f1 or not f2:
            return 0.5
        from difflib import SequenceMatcher
        return SequenceMatcher(None, f1, f2).ratio()

    def _match_cost(mk, gk):
        """Cost for matching model key mk to golden key gk. Lower = better.
        Returns 0.0 for exact match, up to 1.0 for no match."""
        if mk[0] != gk[0]:
            return 1.0  # different dates = impossible match
        return 1.0 - _facility_similarity(mk[1], gk[1])

    def _optimal_match(model_keys, ref_entries, date_only=False):
        """Use Hungarian algorithm for optimal bipartite matching.
        Returns (matched_model_indices, matched_ref_indices, unmatched_model_indices)."""
        if not model_keys or not ref_entries:
            return [], [], list(range(len(model_keys)))
        ref_keys = [_entry_key(e) for e in ref_entries]
        n_model, n_ref = len(model_keys), len(ref_keys)
        import numpy as np
        cost = np.ones((n_model, n_ref), dtype=float)
        for i, mk in enumerate(model_keys):
            for j, rk in enumerate(ref_keys):
                if date_only:
                    cost[i, j] = 0.0 if mk[0] == rk[0] else 1.0
                else:
                    cost[i, j] = _match_cost(mk, rk)
        from scipy.optimize import linear_sum_assignment
        row_ind, col_ind = linear_sum_assignment(cost)
        matched_m, matched_r, unmatched_m = [], [], []
        matched_model_set = set()
        for r, c in zip(row_ind, col_ind):
            if cost[r, c] <= 0.5:  # threshold: at least 50% facility similarity on same date
                matched_m.append(r)
                matched_r.append(c)
                matched_model_set.add(r)
        unmatched_m = [i for i in range(n_model) if i not in matched_model_set]
        return matched_m, matched_r, unmatched_m

    # Phase 1: match model entries to must_extract (Hungarian optimal)
    model_keys_only = [mk for mk, _ in model_keys_list]
    tp_mi, tp_gi, remaining_mi = _optimal_match(model_keys_only, must_extract)

    matched_tp = [model_keys_only[i] for i in tp_mi]
    golden_matched_indices = set(tp_gi)

    # Phase 2: unmatched model entries → try may_extract
    remaining_keys = [model_keys_only[i] for i in remaining_mi]
    may_mi, may_gi, remaining_mi2 = _optimal_match(remaining_keys, may_extract)
    matched_may = [remaining_keys[i] for i in may_mi]

    # Phase 3: still unmatched → try noise (date_only)
    still_remaining = [remaining_keys[i] for i in remaining_mi2]
    noise_mi, noise_gi, final_remaining = _optimal_match(still_remaining, noise_entries, date_only=True)
    matched_noise = [still_remaining[i] for i in noise_mi]

    # Phase 4: classify leftovers as duplicates or FP
    consumed_dates = {mk[0] for mk in matched_tp + matched_may}
    unmatched_fp = []
    duplicates = []
    for i in final_remaining:
        mk = still_remaining[i]
        if mk[0] in consumed_dates:
            duplicates.append(mk)
        else:
            unmatched_fp.append(mk)

    false_negatives = {_entry_key(e) for i, e in enumerate(must_extract) if i not in golden_matched_indices}

    tp = len(matched_tp)
    fp = len(unmatched_fp)
    fn = len(false_negatives)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    false_incl_rate = len(matched_noise) / len(noise_entries) if noise_entries else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_inclusion_rate": round(false_incl_rate, 4),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "false_inclusions": len(matched_noise),
        "may_extract_matched": len(matched_may),
        "total_golden": len(must_extract),
        "total_may_extract": len(may_extract),
        "total_noise": len(noise_entries),
        "total_model_entries": len(model_keys_list),
        "missed_entries": [
            {"date": k[0], "facility": k[1]} for k in false_negatives
        ],
        "extra_entries": [
            {"date": k[0], "facility": k[1]} for k in unmatched_fp
        ],
        "noise_extracted": [
            {"date": k[0], "facility": k[1]} for k in matched_noise
        ],
        "absorbed_may_extract": [
            {"date": k[0], "facility": k[1]} for k in matched_may
        ],
        "duplicates": [
            {"date": k[0], "facility": k[1]} for k in duplicates
        ],
    }


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Synthesize Golden Dataset")
    parser.add_argument("--output", "-o", help="Path to real markdown output (ground truth)")
    parser.add_argument("--out-dir", "-d", help="Output directory for golden dataset")
    parser.add_argument("--style", "-s", default="dde", choices=list(STYLE_DESCRIPTIONS.keys()))
    parser.add_argument("--from-golden", "-g", help="Synthesize from existing golden.json (consensus mode)")
    parser.add_argument("--validate", "-v", help="Validate an existing golden.json")
    parser.add_argument("--evaluate", "-e", nargs=2, metavar=("GOLDEN", "MODEL_OUTPUT"),
                        help="Evaluate model output against golden dataset")
    parser.add_argument("--dry-run", action="store_true",
                        help="Extract entries and show prompt without calling LLM")
    args = parser.parse_args()

    if args.validate:
        print(f"Validating: {args.validate}")
        result = validate_golden(args.validate)
        print(json.dumps(result, indent=2))
        return

    if args.evaluate:
        golden_path, model_path = args.evaluate
        print(f"Evaluating: {model_path} against {golden_path}")
        model_md = Path(model_path).read_text(encoding="utf-8")
        result = evaluate_against_golden(golden_path, model_md)
        print(json.dumps(result, indent=2))
        return

    consensus_may = []  # populated only in --from-golden mode

    # --from-golden: synthesize from existing golden.json (consensus entries)
    if args.from_golden:
        golden_path = Path(args.from_golden)
        with open(golden_path) as f:
            golden = json.load(f)
        out_dir = golden_path.parent
        style = golden.get("style", args.style)
        entries = [e for e in golden["entries"] if e.get("must_extract") is True]
        consensus_may = [e for e in golden["entries"] if e.get("must_extract") == "may_extract"]
        print(f"Loaded {len(entries)} must_extract + {len(consensus_may)} may_extract from {golden_path}")
        # Fall through to synthesis with these entries and this out_dir
        args.out_dir = str(out_dir)
        args.style = style
    elif args.output:
        # Step 1: Parse ground truth markdown
        print(f"Parsing ground truth: {args.output}")
        md_text = Path(args.output).read_text(encoding="utf-8")
        entries = extract_golden_entries(md_text)
        print(f"  Found {len(entries)} entries")
    else:
        parser.error("--output or --from-golden is required for synthesis")

    # Step 2: Build golden.json
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.from_golden:
        golden = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "method": golden.get("method", "multi-model-consensus"),
            "source_outputs": golden.get("source_outputs", ""),
            "consensus_models_used": golden.get("consensus_models_used", 0),
            "consensus_threshold": golden.get("consensus_threshold", 2),
            "style": args.style,
            "source_file": "synthetic_source.txt",
            "total_must_extract": len(entries),
            "total_may_extract": len(consensus_may),
            "entries": list(entries),
        }
    else:
        golden = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_output": str(args.output),
            "style": args.style,
            "source_file": "synthetic_source.txt",
            "total_must_extract": len(entries),
            "entries": entries,
        }

    if args.dry_run:
        print(f"\n  Entries:")
        for e in entries:
            print(f"    {e['encounter_date']} | {e['facility_name']} | {e['visit_type']}")

        entries_for_prompt = []
        for e in entries:
            entry_info = {"date": e["encounter_date"], "facility": e["facility_name"],
                          "provider": e["provider_name"], "visit_type": e["visit_type"]}
            entry_info.update(e.get("key_fields", {}))
            entries_for_prompt.append(entry_info)

        all_dates = [e["encounter_date"] for e in entries]
        date_checklist = "\n".join(f"  - {d}" for d in all_dates)
        prompt = SYNTHESIS_PROMPT.format(
            style_description=STYLE_DESCRIPTIONS[args.style],
            noise_count=NOISE_COUNTS[args.style],
            target_length=f"{TARGET_LENGTHS[args.style]:,}",
            entries_json=json.dumps(entries_for_prompt, indent=2),
            date_checklist=date_checklist,
            entry_count=len(entries),
        )
        print(f"\n  Prompt length: {len(prompt):,} chars")
        print(f"  Target source length: {TARGET_LENGTHS[args.style]:,} chars")
        print(f"\n  Style: {args.style}")
        print(f"  Noise entries to add: {NOISE_COUNTS[args.style]}")
        return

    # Step 3: Synthesize source document
    print(f"\n  Synthesizing source document (style={args.style})...")
    start = time.time()
    source_text = synthesize_source(entries, args.style)
    elapsed = time.time() - start
    print(f"  Generated {len(source_text):,} chars in {elapsed:.1f}s")

    # Step 4a: Collect may_extract entries (from consensus + extra scan)
    golden_dates = {e["encounter_date"] for e in entries}
    may_extract_entries = []
    next_idx = len(entries)

    # If from-golden, include consensus may_extract entries first
    if args.from_golden and consensus_may:
        for me in consensus_may:
            me_copy = dict(me)
            me_copy["index"] = next_idx
            may_extract_entries.append(me_copy)
            next_idx += 1
        if consensus_may:
            print(f"\n  Consensus may_extract: {len(consensus_may)} entries")

    # Scan for extra clinical encounters that LLM may have added during synthesis
    known_dates = golden_dates | {e["encounter_date"] for e in may_extract_entries}
    print(f"  Scanning source for extra clinical encounters...")
    extra_encounters = _scan_for_extra_encounters(source_text, known_dates)
    print(f"  Found {len(extra_encounters)} extra encounter-like segments")

    extra_dates_added = set()
    for enc in extra_encounters:
        d = enc["date"]
        if d in extra_dates_added or d in known_dates:
            continue
        extra_dates_added.add(d)
        may_extract_entries.append({
            "index": next_idx,
            "encounter_date": d,
            "facility_name": enc.get("facility", "Unknown"),
            "provider_name": "Not specified",
            "visit_type": enc.get("description", "Unknown"),
            "must_extract": "may_extract",
            "key_fields": {},
        })
        next_idx += 1

    golden["entries"].extend(may_extract_entries)
    golden["total_may_extract"] = len(may_extract_entries)
    if may_extract_entries:
        print(f"  Total may_extract entries: {len(may_extract_entries)}")
        for me in may_extract_entries:
            print(f"    {me['encounter_date']} | {me['facility_name']} | {me.get('visit_type', '')}")

    # Step 4b: Extract noise dates from source (dates not in golden or may_extract)
    all_known_dates = golden_dates | {e["encounter_date"] for e in may_extract_entries}
    noise_dates = _extract_noise_dates(source_text, all_known_dates)
    print(f"  Found {len(noise_dates)} noise dates in source")

    noise_entries = []
    for i, nd in enumerate(noise_dates):
        noise_entries.append({
            "index": next_idx + i,
            "encounter_date": nd,
            "facility_name": "NOISE",
            "provider_name": "NOISE",
            "visit_type": "administrative/non-clinical",
            "must_extract": False,
            "key_fields": {},
        })
    golden["entries"].extend(noise_entries)
    golden["total_noise"] = len(noise_entries)

    # Step 5: Save
    source_path = out_dir / "synthetic_source.txt"
    source_path.write_text(source_text, encoding="utf-8")

    golden_path = out_dir / "golden.json"
    with open(golden_path, "w") as f:
        json.dump(golden, f, indent=2)

    # Step 5: Auto-validate
    print(f"\n  Validating...")
    validation = validate_golden(str(golden_path))
    print(f"  Coverage: {validation['summary']['coverage']}")
    if validation["warnings"]:
        print(f"  Warnings:")
        for w in validation["warnings"]:
            print(f"    ⚠ {w}")

    validation_path = out_dir / "validation.json"
    with open(validation_path, "w") as f:
        json.dump(validation, f, indent=2)

    print(f"\n  Saved:")
    print(f"    Golden:     {golden_path}")
    print(f"    Source:     {source_path}")
    print(f"    Validation: {validation_path}")
    print(f"\n  Next steps:")
    print(f"    1. Run models against synthetic source:")
    print(f"       python generate_outputs.py -i instruction.txt -s {source_path} -o golden_outputs/{out_dir.name}")
    print(f"    2. Evaluate each model:")
    print(f"       python synthesize_golden.py --evaluate {golden_path} golden_outputs/{out_dir.name}/gemini-2.5-pro/output.md")


if __name__ == "__main__":
    main()
