# Annotation Methodology & Validity

> **[README](README.md)** · **Methodology** · **[Presentation](benchmark_presentation_v2.md)**

**TL;DR:** We evaluate 11 frontier LLMs on extracting structured medical timelines from 6 synthetic golden datasets across 3 rounds. Ground truth is built via multi-model consensus (golden_a–c) and reverse-synthesis (golden_d–f). Evaluation spans 6 dimensions: Extraction F1, Content Fidelity (ROUGE-L), Semantic Fidelity (embeddings), Formatting, Chronological Order, and Hallucination (3-judge LLM ensemble). Statistical significance is established via paired bootstrap (10K iterations). For why this produces reliable ground truth without human annotation, see [§5](#5-mitigation-for-lack-of-human-annotation).

---

## 1. Golden Dataset Construction

### 1.1 Synthetic Source Generation
Each golden dataset is constructed through a **reverse-synthesis** pipeline:

1. A high-quality model output (ground truth chronology) is selected from a top-performing model
2. An LLM synthesizes a realistic source document that would produce the ground truth entries
3. The golden entries are annotated with `must_extract`, `may_extract`, and `noise` labels

This approach guarantees a known ground truth while producing realistic source documents with controlled difficulty levels.

### 1.2 Dataset Diversity
Six golden datasets span different difficulty axes:

| Dataset | Style | Entries | Noise | Challenge |
|---------|-------|---------|-------|-----------|
| Golden A | DDE (Disability) | 7 must + 2 noise | Low | Baseline |
| Golden B | Clinical Notes | 10 must + 2 noise | Low | Multi-provider |
| Golden C | Mixed Format | 5 must + 5 noise | High | Noise discrimination |
| Golden D | Large Document | 15 must + 5 noise | Medium | Long-context |
| Golden E | High Noise | 8 must + 8 noise | Very High | Signal-to-noise |
| Golden F | OCR Degraded | 10 must + 3 noise | Medium | OCR artifacts |

### 1.3 Entry Categories
- **must_extract** (True): Core entries that must appear in the output. Missing = FN.
- **may_extract** ("may_extract"): Borderline entries absorbed silently (not counted as FP or FN).
- **noise** (False): Entries that should NOT be extracted. Extracting = False Inclusion.

> **No human annotation?** Ground truth is algorithmically derived. For why this still produces reliable results, see [§5 — Mitigation for Lack of Human Annotation](#5-mitigation-for-lack-of-human-annotation).

## 2. Evaluation Dimensions

### 2.1 Extraction F1 (Entry-Level)

To compute Precision, Recall, and F1, we must first establish a one-to-one correspondence between model output entries and golden ground truth entries. This is a bipartite matching problem — a model may output entries in any order, with varying facility name formats, so naive exact matching is insufficient.

#### 2.1.1 Hungarian Optimal Matching
We use the **Hungarian algorithm** (Kuhn-Munkres) for bipartite matching between golden and model entries. This guarantees globally optimal matching that is invariant to entry ordering, unlike greedy approaches whose results depend on traversal order.

#### 2.1.2 Facility Fuzzy Matching
Each entry is keyed by `(date, facility)`. Dates must match exactly; facility names are compared using:
1. **Exact match** after normalization (lowercase, alphanumeric only)
2. **SequenceMatcher ratio** for fuzzy similarity (threshold ≥ 0.5)
3. **Empty facility fallback**: if either side has no facility, similarity = 0.5

Cost function: `cost(m, g) = 1.0 - facility_similarity(m, g)` if dates match, else `1.0`.

#### 2.1.3 Multi-Phase Matching
Matching proceeds in four phases to classify every model output entry:

1. **Phase 1 — True Positives**: Hungarian match model entries → `must_extract` golden entries. Matched pairs become TP; unmatched golden entries become FN.
2. **Phase 2 — May-Extract Absorption**: Unmatched model entries are matched against `may_extract` entries. These are absorbed silently — they do not count as FP or FN.
3. **Phase 3 — False Inclusion Detection**: Still-unmatched entries are matched against `noise` entries (date-only matching). Matches here count as False Inclusions.
4. **Phase 4 — FP / Duplicate Classification**: Any remaining entries are classified as duplicates (if their date was already consumed by a TP) or as FP.

#### 2.1.4 Worked Example

A model outputs 12 entries for a dataset with 7 must-extract, 2 may-extract, and 6 noise entries:

```
Model outputs 12 entries
  Phase 1: 6 match must_extract → 6 TP, 1 FN (missed one surgery)
  Phase 2: 2 match may_extract  → absorbed silently (no penalty)
  Phase 3: 1 matches a noise date → 1 False Inclusion
  Phase 4: 3 remaining → 1 duplicate (same date as a TP), 2 FP

  Precision = 6 / (6 + 2) = 75%
  Recall    = 6 / (6 + 1) = 85.7%
  F1        = 80%
```

#### 2.1.5 Metric Definitions
- **Precision**: TP / (TP + FP)
- **Recall**: TP / (TP + FN)
- **F1**: Harmonic mean of Precision and Recall
- **False Inclusion Rate**: Noise entries extracted / Total noise entries

### 2.2 Content Fidelity (per matched TP pair)
For each TP-matched entry pair, field-level text quality is measured by:
- **ROUGE-L F1**: Longest common subsequence overlap
- **Token Overlap (Jaccard)**: Set intersection over union of tokens
- **Semantic Fidelity**: Cosine similarity of sentence embeddings (all-MiniLM-L6-v2)

### 2.3 Structural Compliance
- **Formatting Score**: Markdown structure compliance (headers, fields, etc.)
- **Chronological Score**: Date ordering compliance
- **Citation Validation**: Source reference accuracy

### 2.4 Hallucination Detection (Multi-Judge)
- **Claim Extraction**: Atomic claims extracted from model output
- **3-Judge Ensemble**: Gemini, GPT, Claude independently verify each claim against source
- **Majority Voting**: Claim classified as Supported/Unsupported/Partial by 2-of-3 agreement
- **Score**: (Supported + 0.5×Partial) / Total Claims

## 3. Statistical Rigor

### 3.1 Multi-Round Evaluation
Each model is evaluated across **3 independent rounds** (separate generation runs) to measure output stability. Results report mean ± standard deviation.

### 3.2 Paired Bootstrap Significance Test
- **Metric**: Composite score (F1×30% + Semantic×20% + Halluc×20% + Fmt×10% + Chrono×10% + ROUGE×10%)
- **10,000 bootstrap iterations** per model pair
- Sample units: (round, golden_dataset) pairs — 18 paired observations per model pair
- Reports: p-value, 95% CI, Cohen's d effect size
- Significance threshold: p < 0.05
- Composite-based testing provides more differentiation than F1 alone (which is near-ceiling for all models)

### 3.3 Cross-Validation
Deterministic metrics (Semantic Fidelity, ROUGE-L) are correlated with LLM-judge hallucination scores to verify alignment between objective and subjective evaluation.

## 4. Validity Considerations

### 4.1 Construct Validity
The benchmark measures what it claims to measure:
- **Entry extraction**: Directly measured by P/R/F1 against known ground truth
- **Content fidelity**: Multi-metric triangulation (ROUGE-L, token overlap, embedding similarity)
- **Hallucination**: Independent multi-judge ensemble reduces single-judge bias

### 4.2 Internal Validity
- **Controlled variables**: Same instruction, same source document per dataset
- **Randomization**: Multiple rounds with independent LLM generation
- **Blinding**: Judges evaluate claims without knowing which model produced them

### 4.3 External Validity
- **Dataset diversity**: 6 datasets spanning different document styles and difficulty levels
- **Model diversity**: 11 models from 5 providers (Google, OpenAI, Anthropic, Alibaba, MiniMax)
- **Limitation**: Synthetic sources may not capture all real-world document complexities

### 4.3.1 Serving Conditions & Quantization
Not all models are served at the same numerical precision, which may affect results:

| Model | Provider | Serving | Precision |
|-------|----------|---------|-----------|
| Gemini 2.5 Pro/Flash, 3 Flash, 3.1 Pro | Google API | Official API | Undisclosed |
| GPT-5.4, GPT-5.4-Pro, GPT-5.4-Mini | OpenAI API | Official API | Undisclosed |
| Claude Opus 4.6, Claude Opus 4.5 | Anthropic API | Official API | Undisclosed |
| Qwen3-235B (†) | Nebius | Dedicated endpoint | **FP16** |
| MiniMax-M2.5 (‡) | Nebius | Serverless | **FP4** |

**Impact**: FP4 quantization (MiniMax-M2.5) is an aggressive compression that may degrade model quality compared to full-precision (FP16/BF16) serving. Results for MiniMax-M2.5 should be interpreted with this caveat — lower scores may partially reflect quantization loss rather than inherent model capability. Closed-source models' serving precision is not disclosed by their providers.

### 4.4 Reliability
- **Inter-judge agreement**: Reported per evaluation (typically 85-95%)
- **Test-retest reliability**: Multi-round evaluation captures generation variance
- **Reproducibility**: All code, data, and configurations are version-controlled

### 4.5 Known Limitations
1. **Synthetic data**: Golden datasets use LLM-synthesized sources, not real medical records
2. **No human annotation**: Ground truth is algorithmically derived, not human-verified
3. **Single task**: Benchmark covers medical chronology extraction only
4. **Unequal serving precision**: MiniMax-M2.5 served at FP4 quantization; Qwen3-235B at FP16; closed-source models' precision undisclosed (see §4.3.1)
5. **English only**: All datasets are in English

## 5. Mitigation for Lack of Human Annotation

Instead of direct human annotation (which requires domain experts and is cost-prohibitive), we employ:

1. **Cross-Model Consensus**: If 10+ models agree on an extraction, it reinforces the golden label
2. **Self-Consistency Validation**: Each golden dataset is validated by re-running the synthesis pipeline and checking for convergence
3. **Multi-Judge Ensemble**: 3 independent LLM judges with majority voting reduces bias
4. **Deterministic Cross-Validation**: Objective metrics (embedding similarity, ROUGE-L) are correlated with subjective judge scores to verify alignment
5. **Error Analysis**: Systematic identification of failure patterns across models and datasets

## 6. Reproducibility Checklist

- [x] All code is version-controlled (Git)
- [x] Dependencies are pinned (requirements.txt with exact versions)
- [x] Random seeds are fixed where applicable
- [x] All evaluation scripts are deterministic (given same inputs)
- [x] Model configurations are recorded in models.json
- [x] Serving conditions and quantization levels are documented (see §4.3.1)
- [x] Per-run metadata (tokens, latency, timestamps) is saved
- [x] Results are machine-readable (JSON) and human-readable (Markdown)
