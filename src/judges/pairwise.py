"""
Pairwise Comparison Judge.

Compares two model outputs side-by-side using chunked LLM calls.
Each chunk covers a subset of entries with their relevant source
context, avoiding context-window limits and improving accuracy.
Results are aggregated via majority vote across chunks.
"""

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from .base import LLMJudge


MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
MONTH_ABBR = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

DIMENSIONS = ["completeness", "accuracy", "hallucination"]


@dataclass
class PairwiseVerdict:
    """Result of comparing two models."""
    model_a: str
    model_b: str
    winner: str  # model_a name | model_b name | "tie"
    dimensions: Dict[str, str] = field(default_factory=dict)  # dimension -> winner
    reasoning: str = ""
    chunk_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "model_a": self.model_a,
            "model_b": self.model_b,
            "winner": self.winner,
            "dimensions": self.dimensions,
            "reasoning": self.reasoning,
        }
        if self.chunk_count > 1:
            d["chunk_count"] = self.chunk_count
        return d


@dataclass
class PairwiseResult:
    """Aggregate pairwise comparison results."""
    comparisons: List[PairwiseVerdict] = field(default_factory=list)
    win_counts: Dict[str, int] = field(default_factory=dict)
    elo_scores: Dict[str, float] = field(default_factory=dict)

    def compute_rankings(self):
        """Compute win counts and simple Elo from pairwise results."""
        self.win_counts = {}
        for v in self.comparisons:
            for name in [v.model_a, v.model_b]:
                if name not in self.win_counts:
                    self.win_counts[name] = 0
            if v.winner != "tie":
                self.win_counts[v.winner] = self.win_counts.get(v.winner, 0) + 1

        # Simple Elo (start at 1000, K=32)
        self.elo_scores = {name: 1000.0 for name in self.win_counts}
        for v in self.comparisons:
            if v.winner == "tie":
                continue
            ea = 1 / (1 + 10 ** ((self.elo_scores[v.model_b] - self.elo_scores[v.model_a]) / 400))
            eb = 1 - ea
            if v.winner == v.model_a:
                self.elo_scores[v.model_a] += 32 * (1 - ea)
                self.elo_scores[v.model_b] += 32 * (0 - eb)
            else:
                self.elo_scores[v.model_a] += 32 * (0 - ea)
                self.elo_scores[v.model_b] += 32 * (1 - eb)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "comparisons": [c.to_dict() for c in self.comparisons],
            "win_counts": self.win_counts,
            "elo_scores": {k: round(v, 1) for k, v in self.elo_scores.items()},
        }


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

CHUNK_PROMPT_JSON = """You are a medical-legal document review expert. Compare two model outputs that extracted medical encounters from the same source document.

You are reviewing **chunk {chunk_idx}/{chunk_total}** — a subset of entries covering specific encounter dates. Focus ONLY on the entries and source context shown below.

## Source Context for These Encounters
{source_excerpt}

## Model A ({model_a_name}) — {model_a_count} entries in this chunk (total across all chunks: {model_a_total})
```json
{model_a_sample}
```

## Model B ({model_b_name}) — {model_b_count} entries in this chunk (total across all chunks: {model_b_total})
```json
{model_b_sample}
```

## Evaluation Dimensions

Analyze EACH dimension in detail (2-3 sentences each), then give your verdict for THIS chunk.

1. **Completeness**: Which model extracted more relevant encounters from the source context shown? Did either miss encounters visible in the source above?
2. **Accuracy**: Which model has more accurate dates, provider names, facility names, and clinical details? Identify specific errors if any.
3. **Hallucination**: Did either model fabricate encounters, providers, dates, or clinical details NOT present in the source above? Most critical for medical-legal work.

## Response Format

First, write your detailed analysis for each dimension. Then end with EXACTLY this format:

DIMENSIONS:
completeness: A or B or tie
accuracy: A or B or tie
hallucination: A or B or tie

WINNER: A or B or tie

REASONING: <one paragraph explaining the verdict for this chunk>
"""

PAIRWISE_PROMPT_MARKDOWN = """You are a medical-legal document review expert. Compare two model outputs generated from the same source document and instruction.

## Source Document (excerpt)
{source_excerpt}

## Model A Output ({model_a_name})
{model_a_sample}

## Model B Output ({model_b_name})
{model_b_sample}

## Evaluation Dimensions

Analyze EACH dimension in detail (2-3 sentences each), then give your final verdict.

1. **Completeness**: Which model captured more relevant medical information from the source? Did either miss important encounters, findings, or details?
2. **Accuracy**: Which model has more accurate facts, dates, provider names, and clinical details? Identify specific errors if any.
3. **Hallucination**: Did either model fabricate information NOT present in the source document? This is the most critical dimension for medical-legal work.

## Response Format

First, write your detailed analysis for each dimension. Then end with EXACTLY this format:

DIMENSIONS:
completeness: A or B or tie
accuracy: A or B or tie
hallucination: A or B or tie

WINNER: A or B or tie

REASONING: <one paragraph explaining the overall verdict>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _date_to_search_variants(date_str: str) -> List[str]:
    """Convert YYYY-MM-DD to all formats that might appear in source text."""
    try:
        y, m, d = date_str.split("-")
        m_int, d_int = int(m), int(d)
    except (ValueError, IndexError):
        return [date_str]

    variants = [
        date_str,                                        # 2024-01-15
        f"{m}/{d}/{y}",                                  # 01/15/2024
        f"{m_int}/{d_int}/{y}",                          # 1/15/2024
        f"{m}/{d_int}/{y}",                              # 01/15/2024
        f"{m_int}/{d}/{y}",                              # 1/15/2024
    ]
    if 1 <= m_int <= 12:
        variants += [
            f"{MONTH_NAMES[m_int]} {d_int}, {y}",        # January 15, 2024
            f"{MONTH_ABBR[m_int]} {d_int}, {y}",         # Jan 15, 2024
            f"{MONTH_ABBR[m_int]}. {d_int}, {y}",        # Jan. 15, 2024
        ]
    return list(dict.fromkeys(variants))


def _find_source_segments(
    dates: List[str],
    source_text: str,
    context_window: int = 1500,
) -> str:
    """Find and merge source segments around the given dates."""
    segments: List[Tuple[int, int]] = []
    for date_str in dates:
        for variant in _date_to_search_variants(date_str):
            idx = 0
            while True:
                pos = source_text.find(variant, idx)
                if pos == -1:
                    break
                seg_start = max(0, pos - context_window)
                seg_end = min(len(source_text), pos + len(variant) + context_window)
                segments.append((seg_start, seg_end))
                idx = pos + 1

    if not segments:
        return ""

    segments.sort()
    merged = [segments[0]]
    for start, end in segments[1:]:
        if start <= merged[-1][1] + 200:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    return "\n\n[...]\n\n".join(source_text[s:e] for s, e in merged)


def _majority_vote(votes: List[str], name_a: str, name_b: str) -> str:
    """Return the majority winner from a list of votes."""
    counts = Counter(votes)
    a_wins = counts.get(name_a, 0)
    b_wins = counts.get(name_b, 0)
    if a_wins > b_wins:
        return name_a
    if b_wins > a_wins:
        return name_b
    return "tie"


# ---------------------------------------------------------------------------
# Judge
# ---------------------------------------------------------------------------

class PairwiseJudge(LLMJudge):
    """Compare two model outputs using chunked LLM calls.

    For JSON (list-type) outputs, entries are grouped by date into
    chunks of ``dates_per_chunk`` dates.  Each chunk is sent to the
    Judge with only the relevant source context.  Results are
    aggregated via majority vote.

    For raw markdown outputs, a single call is made with a prefix of
    the source document.
    """

    def __init__(
        self,
        dates_per_chunk: int = 8,
        context_window: int = 1500,
        source_excerpt_len: int = 30000,
        **kwargs,
    ):
        super().__init__(max_tokens=4096, **kwargs)
        self.dates_per_chunk = dates_per_chunk
        self.context_window = context_window
        self.source_excerpt_len = source_excerpt_len

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compare_all(
        self,
        model_outputs: Dict[str, Tuple[List[Dict], str]],
        source_text: str,
        verbose: bool = False,
    ) -> PairwiseResult:
        """Run pairwise comparisons between all model pairs."""
        names = list(model_outputs.keys())
        result = PairwiseResult()

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                name_a, name_b = names[i], names[j]
                entries_a, raw_a = model_outputs[name_a]
                entries_b, raw_b = model_outputs[name_b]

                if verbose:
                    print(f"   Comparing: {name_a} vs {name_b}")

                verdict = self._compare_pair(
                    name_a, entries_a, raw_a,
                    name_b, entries_b, raw_b,
                    source_text,
                    verbose,
                )
                result.comparisons.append(verdict)

        result.compute_rankings()
        return result

    # ------------------------------------------------------------------
    # Core comparison logic
    # ------------------------------------------------------------------

    def _compare_pair(
        self,
        name_a: str, entries_a: List[Dict], raw_a: str,
        name_b: str, entries_b: List[Dict], raw_b: str,
        source_text: str,
        verbose: bool = False,
    ) -> PairwiseVerdict:
        """Compare two model outputs (JSON entries or raw markdown)."""
        included_a = [e for e in entries_a if isinstance(e, dict) and e.get("include") is True]
        included_b = [e for e in entries_b if isinstance(e, dict) and e.get("include") is True]

        use_json = bool(included_a or included_b)

        if use_json:
            return self._chunked_json_compare(
                name_a, included_a,
                name_b, included_b,
                source_text, verbose,
            )
        else:
            return self._single_markdown_compare(
                name_a, raw_a, name_b, raw_b, source_text,
            )

    def _chunked_json_compare(
        self,
        name_a: str, included_a: List[Dict],
        name_b: str, included_b: List[Dict],
        source_text: str,
        verbose: bool = False,
    ) -> PairwiseVerdict:
        """Split entries into date-based chunks, call Judge per chunk, aggregate."""

        # 1. Collect all unique dates from both models, sorted chronologically
        all_dates: set = set()
        for e in included_a + included_b:
            d = e.get("encounter_date")
            if d and isinstance(d, str):
                all_dates.add(d)
        sorted_dates = sorted(all_dates)

        if not sorted_dates:
            return PairwiseVerdict(
                model_a=name_a, model_b=name_b, winner="tie",
                reasoning="No encounter dates found in either model output.",
            )

        # 2. Split dates into chunks
        chunks: List[List[str]] = []
        for i in range(0, len(sorted_dates), self.dates_per_chunk):
            chunks.append(sorted_dates[i:i + self.dates_per_chunk])

        if verbose:
            print(f"     {len(sorted_dates)} unique dates → {len(chunks)} chunk(s)")

        # 3. Build index: date → entries for each model
        a_by_date: Dict[str, List[Dict]] = {}
        for e in included_a:
            d = e.get("encounter_date", "")
            a_by_date.setdefault(d, []).append(e)

        b_by_date: Dict[str, List[Dict]] = {}
        for e in included_b:
            d = e.get("encounter_date", "")
            b_by_date.setdefault(d, []).append(e)

        # 4. Call Judge for each chunk, collect per-chunk verdicts
        chunk_verdicts: List[PairwiseVerdict] = []
        for ci, date_chunk in enumerate(chunks):
            chunk_a = []
            chunk_b = []
            for d in date_chunk:
                chunk_a.extend(a_by_date.get(d, []))
                chunk_b.extend(b_by_date.get(d, []))

            # Also include entries from model A/B whose dates are NOT in the
            # other model at all (unique to one side) — these are important
            # for completeness/hallucination judgement.
            # They are already captured because all_dates is the union.

            source_excerpt = _find_source_segments(
                date_chunk, source_text, self.context_window,
            )
            if not source_excerpt:
                source_excerpt = "(No matching source context found for these dates)"

            prompt = CHUNK_PROMPT_JSON.format(
                chunk_idx=ci + 1,
                chunk_total=len(chunks),
                source_excerpt=source_excerpt,
                model_a_name=name_a,
                model_a_count=len(chunk_a),
                model_a_total=len(included_a),
                model_a_sample=json.dumps(chunk_a, indent=2),
                model_b_name=name_b,
                model_b_count=len(chunk_b),
                model_b_total=len(included_b),
                model_b_sample=json.dumps(chunk_b, indent=2),
            )

            try:
                response = self.generate(prompt)
                v = self._parse_response(response, name_a, name_b)
            except Exception as e:
                v = PairwiseVerdict(
                    model_a=name_a, model_b=name_b, winner="tie",
                    reasoning=f"Chunk {ci+1} error: {e}",
                )

            chunk_verdicts.append(v)
            if verbose:
                dims_str = " ".join(f"{k}={v_}" for k, v_ in v.dimensions.items())
                print(f"     Chunk {ci+1}/{len(chunks)}: winner={v.winner}  {dims_str}")

        # 5. Aggregate via majority vote
        return self._aggregate_chunk_verdicts(
            chunk_verdicts, name_a, name_b,
        )

    def _aggregate_chunk_verdicts(
        self,
        chunk_verdicts: List[PairwiseVerdict],
        name_a: str,
        name_b: str,
    ) -> PairwiseVerdict:
        """Aggregate per-chunk verdicts into a single PairwiseVerdict."""
        if len(chunk_verdicts) == 1:
            v = chunk_verdicts[0]
            v.chunk_count = 1
            return v

        # Per-dimension majority vote
        dim_results: Dict[str, str] = {}
        for dim in DIMENSIONS:
            votes = [v.dimensions.get(dim, "tie") for v in chunk_verdicts]
            dim_results[dim] = _majority_vote(votes, name_a, name_b)

        # Overall winner = majority of dimension winners
        dim_winners = list(dim_results.values())
        overall_winner = _majority_vote(dim_winners, name_a, name_b)

        # Collect reasoning summaries
        reasons = []
        for i, v in enumerate(chunk_verdicts):
            short = v.reasoning[:150].replace("\n", " ") if v.reasoning else ""
            reasons.append(f"[Chunk {i+1}: {v.winner}] {short}")
        combined_reasoning = " | ".join(reasons)

        return PairwiseVerdict(
            model_a=name_a,
            model_b=name_b,
            winner=overall_winner,
            dimensions=dim_results,
            reasoning=combined_reasoning,
            chunk_count=len(chunk_verdicts),
        )

    def _single_markdown_compare(
        self,
        name_a: str, raw_a: str,
        name_b: str, raw_b: str,
        source_text: str,
    ) -> PairwiseVerdict:
        """Fallback: single-call comparison for raw markdown outputs."""
        prompt = PAIRWISE_PROMPT_MARKDOWN.format(
            source_excerpt=source_text[:self.source_excerpt_len],
            model_a_name=name_a,
            model_a_sample=raw_a[:15000],
            model_b_name=name_b,
            model_b_sample=raw_b[:15000],
        )
        try:
            response = self.generate(prompt)
            return self._parse_response(response, name_a, name_b)
        except Exception as e:
            return PairwiseVerdict(
                model_a=name_a, model_b=name_b, winner="tie",
                reasoning=f"Error: {e}",
            )

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _resolve_label(self, raw: str, name_a: str, name_b: str) -> str:
        """Map 'A', 'B', model names, or 'tie' to the canonical winner string."""
        val = raw.strip().upper()
        if val == "A" or name_a.upper() in val:
            return name_a
        if val == "B" or name_b.upper() in val:
            return name_b
        return "tie"

    def _parse_response(self, response: str, name_a: str, name_b: str) -> PairwiseVerdict:
        """Parse free-text LLM response into PairwiseVerdict.

        Expected tail format:
            DIMENSIONS:
            completeness: A or B or tie
            accuracy: A or B or tie
            hallucination: A or B or tie

            WINNER: A or B or tie

            REASONING: ...
        Falls back to JSON parsing for backward compatibility.
        """
        dimensions: Dict[str, str] = {}
        winner = "tie"
        reasoning = ""

        # --- Try structured tail parsing first ---
        winner_match = re.search(r'WINNER:\s*(.+)', response, re.IGNORECASE)
        if winner_match:
            winner = self._resolve_label(winner_match.group(1), name_a, name_b)

        dim_block = re.search(r'DIMENSIONS:\s*\n((?:\s*\w+:\s*.+\n?)+)', response, re.IGNORECASE)
        if dim_block:
            for line in dim_block.group(1).strip().splitlines():
                parts = line.split(":", 1)
                if len(parts) == 2:
                    dim_name = parts[0].strip().lower()
                    dim_val = self._resolve_label(parts[1], name_a, name_b)
                    dimensions[dim_name] = dim_val

        reason_match = re.search(r'REASONING:\s*(.+)', response, re.IGNORECASE | re.DOTALL)
        if reason_match:
            reasoning = reason_match.group(1).strip()

        if winner_match:
            return PairwiseVerdict(
                model_a=name_a,
                model_b=name_b,
                winner=winner,
                dimensions=dimensions,
                reasoning=reasoning,
            )

        # --- Fallback: JSON parsing (backward compat) ---
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[len("```json"):].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            try:
                data = json.loads(json_match.group())
                winner = self._resolve_label(data.get("winner", "tie"), name_a, name_b)
                for dim, val in data.get("dimensions", {}).items():
                    dimensions[dim] = self._resolve_label(str(val), name_a, name_b)
                reasoning = data.get("reasoning", "")

                return PairwiseVerdict(
                    model_a=name_a,
                    model_b=name_b,
                    winner=winner,
                    dimensions=dimensions,
                    reasoning=reasoning,
                )
            except (json.JSONDecodeError, ValueError):
                pass

        return PairwiseVerdict(
            model_a=name_a,
            model_b=name_b,
            winner="tie",
            reasoning=f"Could not parse response: {response[:300]}",
        )
