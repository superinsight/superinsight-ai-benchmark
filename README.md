# Medical Chronology LLM Benchmark

![License](https://img.shields.io/badge/license-Apache%202.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Tests](https://img.shields.io/badge/tests-104%20passed-brightgreen)
![Models](https://img.shields.io/badge/models-11%20evaluated-orange)

> **[Methodology](METHODOLOGY.md)** · **[Presentation (Marp)](benchmark_presentation_v2.md)** · **[env.example](env.example)**

**Can LLMs reliably extract structured medical timelines from unstructured records?**

In medical-legal cases, a *Medical Chronology* is the foundation of case review — a structured timeline of every clinical encounter extracted from hundreds of pages of unstructured records. Producing one manually takes 8–20 hours per case. LLMs promise to automate this, but accuracy is non-negotiable: a single hallucinated diagnosis or missed surgery can change the outcome of a lawsuit.

This benchmark evaluates **11 frontier LLMs** across **6 golden datasets**, **3 independent rounds**, and **6 evaluation dimensions** — from extraction accuracy to hallucination detection — with full statistical rigor.

![Overall F1 Ranking](charts/0_overall_f1_ranking.png)

> Render the full 30-slide presentation with [Marp](https://marp.app/): `marp benchmark_presentation_v2.md -o presentation.pdf`

## Key Results

| Tier | Models | Composite | F1 | Hallucination |
|:----:|--------|:---------:|:--:|:------------:|
| **S** | claude-opus-4.6 | 0.889 | 100.0% | 94.0% |
| **A** | claude-opus-4.5, gemini-2.5-flash, gemini-3-flash | 0.866–0.877 | 99.6–100% | 90.7–93.9% |
| **B** | gpt-5.4, gpt-5.4-mini, gpt-5.4-pro | 0.867–0.871 | 96.9–97.3% | 86.3–95.4% |
| **C** | qwen3-235b†, gemini-2.5-pro, minimax-m2.5‡, gemini-3.1-pro | 0.847–0.859 | 97.8–99.2% | 81.2–92.4% |

> † FP16 (Nebius dedicated) · ‡ FP4 (Nebius serverless) · unmarked = official API (precision undisclosed)

**How to read:** S-tier is statistically significantly better than all lower tiers (p<0.05, paired bootstrap, 10K iterations). Within a tier, differences are not significant — models are interchangeable. Composite = F1 30% + Semantic 20% + Halluc 20% + Fmt 10% + Chrono 10% + ROUGE 10%. See [METHODOLOGY.md](METHODOLOGY.md) for full details.

## What This Benchmark Measures

Given an unstructured medical record, can the LLM extract a structured chronological timeline of clinical encounters?

```
Source Document (unstructured)          Golden Ground Truth
  "Patient seen 01/15/2023 at            ┌─ Date: 01/15/2023
   St. Mary Hospital by Dr. Smith         │  Facility: St. Mary Hospital
   for Type 2 Diabetes..."                │  Provider: Dr. Smith
         │                                │  Diagnoses: Type 2 Diabetes
         ▼                                └─ Plan: Metformin 500mg
   LLM extracts structured timeline
         │
         ▼
   Compare across 6 dimensions ──→ Precision, Recall, F1, Fidelity, Hallucination
```

Six evaluation dimensions:

| Dimension | Method | What It Measures |
|-----------|--------|-----------------|
| **Extraction F1** | Hungarian matching vs golden ground truth | Did the model find the right encounters? |
| **Content Fidelity** | ROUGE-L F1 | Does extracted text match golden fields? |
| **Semantic Fidelity** | Embedding cosine similarity | Semantic equivalence beyond surface text |
| **Formatting** | Deterministic | Markdown structure, headings, field labels |
| **Chronological** | Deterministic | Dates in ascending order |
| **Hallucination** | Multi-judge LLM ensemble (3 judges, majority vote) | Are claims supported by source? |

## Golden Datasets

| Dataset | Style | Must | May | Noise | Tokens | Design Intent |
|---------|-------|:---:|:---:|:---:|:---:|:---:|
| **golden_a** | DDE | 7 | 2 | 6 | 4.4K | Baseline — short, clean DDE |
| **golden_b** | Clinical Note | 10 | 1 | 8 | 11.1K | Paraphrasing stress test |
| **golden_c** | Mixed | 5 | 3 | 15 | 7.6K | Noise filtering (highest noise ratio) |
| **golden_d** | DDE | 15 | 0 | 13 | 7.2K | Volume stress (15 entries) |
| **golden_e** | Mixed | 8 | 0 | 5 | 7.0K | Balanced difficulty |
| **golden_f** | Mixed | 10 | 0 | 9 | 14.4K | OCR degradation + long document |

Ground truth is built via **multi-model consensus** (golden_a–c) and **synthetic reverse-design** (golden_d–f). See [METHODOLOGY.md](METHODOLOGY.md) §1 for construction details.

## Serving Conditions

Not all models are served at the same numerical precision:

| Model | Provider | Precision |
|-------|----------|-----------|
| Gemini 2.5 Pro/Flash, 3 Flash, 3.1 Pro | Google API | Undisclosed |
| GPT-5.4, GPT-5.4-Pro, GPT-5.4-Mini | OpenAI API | Undisclosed |
| Claude Opus 4.6, Claude Opus 4.5 | Anthropic API | Undisclosed |
| Qwen3-235B (†) | Nebius dedicated | **FP16** |
| MiniMax-M2.5 (‡) | Nebius serverless | **FP4** |

FP4 quantization may degrade quality compared to full-precision serving. Results for MiniMax-M2.5 should be interpreted with this caveat.

## Quick Start

### Try It Without API Keys

All model outputs and evaluation results are included in this repo. You can explore the results immediately:

```bash
pip install -r requirements.txt

# Evaluate pre-generated outputs — no API keys needed, runs in ~5 seconds
python evaluate_golden_only.py
```

This runs the full F1 evaluation pipeline (Hungarian matching, formatting, chronological order) on all 198 pre-generated model outputs and prints the leaderboard.

### Full Pipeline (Requires API Keys)

To generate new model outputs or run LLM-judge hallucination evaluation, you need at least one provider API key. The quickest setup is a single line — `OPENAI_API_KEY` or `GOOGLE_AI_STUDIO_API_KEY`:

```bash
cp env.example .env
# Edit .env — set at least one provider API key
```

### 1. Generate Model Outputs

```bash
# Run all configured models on a golden dataset
python generate_outputs.py \
  --instruction instruction.txt \
  --source golden/golden_a/synthetic_source.txt \
  --output-dir golden_outputs/round_1/golden_a \
  --models-config models.json

# Or run a single model
python generate_outputs.py \
  --instruction instruction.txt \
  --source golden/golden_a/synthetic_source.txt \
  --model gemini:gemini-2.5-pro:gemini-2.5-pro
```

### 2. Evaluate Extraction (F1, Formatting, Chronological, Content Fidelity)

```bash
# Evaluate all rounds against golden ground truth
python evaluate_golden_only.py

# Evaluate with semantic fidelity
python evaluate_deterministic.py
```

### 3. Evaluate Hallucination

```bash
# Multi-judge evaluation (Gemini + GPT + Claude)
python evaluate_hallucination.py \
  --round 1 \
  --golden golden_a
```

### 4. Statistical Significance

```bash
# Paired bootstrap test across all model pairs
python evaluate_bootstrap.py --n-boot 10000
```

### 5. Generate Charts & Presentation

```bash
# Generate all charts
python generate_charts.py

# Generate leaderboard
python generate_leaderboard.py
```

### Adding a New Model (Incremental)

Use `scripts/add_model.sh` to run the full pipeline for a single new model without re-evaluating existing ones:

```bash
# One command — handles everything
./scripts/add_model.sh openai:gpt-6:gpt-6

# Format: provider:model_id:label
./scripts/add_model.sh gemini:gemini-4-pro:gemini-4-pro
./scripts/add_model.sh nebius:MiniMaxAI/MiniMax-M3:minimax-m3
./scripts/add_model.sh anthropic:claude-5:claude-5
```

The script will:
1. Generate outputs (skips existing `output.md` files)
2. Re-run F1 and deterministic evaluation (fast, deterministic)
3. Run hallucination evaluation **only for the new model** (`--incremental`)
4. Re-run bootstrap significance test
5. Regenerate leaderboard and charts

You can also run hallucination evaluation incrementally by itself:

```bash
# Only evaluate a specific model, skip already-evaluated combos
python evaluate_hallucination.py --rounds 3 --judges all --models my-new-model --incremental
```

## Project Structure

```
benchmark/
├── README.md                       # This file
├── METHODOLOGY.md                  # Detailed methodology & validity analysis
├── benchmark_presentation_v2.md    # Marp presentation
├── models.json                     # Model configurations
├── instruction.txt                 # Extraction instruction prompt
│
├── golden/                         # Golden datasets
│   ├── golden_a/
│   │   ├── golden.json             # Ground truth entries
│   │   └── synthetic_source.txt    # Source document
│   ├── golden_b/ ... golden_f/
│
├── golden_outputs/                 # Model outputs & evaluation results
│   ├── round_1/ ... round_3/      # Per-round model outputs
│   ├── golden_benchmark_aggregated.json
│   ├── deterministic_results.json
│   ├── hallucination_results.json
│   └── bootstrap_results.json
│
├── charts/                         # Generated visualizations
│
├── generate_outputs.py             # Run models on golden datasets
├── evaluate_golden_only.py         # F1 evaluation
├── evaluate_deterministic.py       # Semantic + ROUGE-L evaluation
├── evaluate_hallucination.py       # Multi-judge hallucination
├── evaluate_bootstrap.py           # Statistical significance (composite)
├── evaluate_error_analysis.py      # Systematic failure patterns
├── evaluate_cross_validation.py    # Metric correlation analysis
├── generate_charts.py              # Chart generation
├── generate_leaderboard.py         # Leaderboard generation
├── synthesize_golden.py            # Golden dataset construction
├── build_consensus_golden.py       # Multi-model consensus builder
│
├── scripts/                        # Shell runner scripts
│   ├── add_model.sh                # Incremental model addition
│   ├── run_golden_def.sh           # Run golden D/E/F
│   └── run_golden_*.sh             # Other batch runners
│
├── tests/                          # All tests
│   ├── test_scoring.py
│   ├── test_validators.py
│   └── ...
│
├── tools/                          # One-off / utility scripts
│   ├── extract_section.py
│   ├── extract_source.py
│   └── visualize_results.py
│
├── config/                         # Archived / alternate configs
│   ├── models_gemini_only.json
│   └── models_new.json
│
├── llm/                            # Bundled LLM client (self-contained)
│   ├── base.py                     # LLMConfig, LLMProvider base class
│   ├── client.py                   # LLMClient factory
│   ├── gemini.py                   # Google Gemini/Vertex AI
│   ├── nebius.py                   # Nebius (OpenAI-compatible)
│   └── bedrock.py                  # AWS Bedrock
│
├── environment.py                  # Environment variable configuration
│
└── src/                            # Shared library
    ├── contracts/
    ├── judges/
    ├── scoring/
    ├── utils/
    └── validators/
```

## Evaluation Pipeline

```
Golden Datasets (6)
       │
       ▼
Generate Outputs ──→ 11 models × 3 rounds × 6 datasets = 198 runs
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│  Deterministic Evaluation                                │
│  ├── F1 (Hungarian matching)                             │
│  ├── ROUGE-L (field-level)                               │
│  ├── Semantic Fidelity (embedding cosine similarity)     │
│  ├── Formatting (markdown structure)                     │
│  └── Chronological Order (date sequence)                 │
└──────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│  LLM-Judge Evaluation                                    │
│  ├── Claim extraction from model output                  │
│  ├── 3-judge ensemble (Gemini + GPT + Claude)            │
│  └── Majority voting → Supported / Unsupported / Partial │
└──────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│  Statistical Analysis                                    │
│  ├── Paired bootstrap significance (10K iterations)      │
│  ├── Error analysis (systematic failure patterns)        │
│  └── Cross-validation (metric correlation)               │
└──────────────────────────────────────────────────────────┘
       │
       ▼
Charts + Presentation + Leaderboard
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Matching** | Hungarian algorithm | Globally optimal bipartite matching, order-invariant |
| **Facility matching** | Fuzzy (SequenceMatcher ≥ 0.5) | Handles abbreviations and minor variations |
| **Hallucination judges** | 3-model ensemble | Reduces single-model bias |
| **Rounds** | 3 per model | Captures generation variance |
| **Bootstrap** | 10K iterations, paired | Controls for dataset difficulty |
| **Composite score** | F1 30% + Semantic 20% + Halluc 20% + Fmt 10% + Chrono 10% + ROUGE 10% | Weights reflect task priorities |

## Environment Variables

See [env.example](env.example) for all available configuration.

**Minimum:** Set at least one provider to generate outputs or run hallucination judges. Evaluation scripts (`evaluate_golden_only.py`, `evaluate_deterministic.py`, `evaluate_bootstrap.py`) work without any API keys.

```bash
# At least one provider — pick the one(s) you have access to
OPENAI_API_KEY=...                   # GPT-5.4 family
GOOGLE_AI_STUDIO_API_KEY=...         # Gemini 3+ (AI Studio)
GOOGLE_APPLICATION_CREDENTIALS=...   # Gemini 2.5 (Vertex AI)
ANTHROPIC_API_KEY=...                # Claude Opus family
NEBIUS_API_KEY=...                   # Qwen3, MiniMax (Nebius)

# Optional
EMBEDDING_MODEL=all-MiniLM-L6-v2    # For semantic fidelity (default: all-MiniLM-L6-v2)
```

## Known Limitations

1. **Synthetic data** — golden datasets use LLM-synthesized sources, not real medical records
2. **No human annotation** — ground truth is algorithmically derived (see METHODOLOGY.md §5)
3. **Unequal serving precision** — MiniMax-M2.5 at FP4, Qwen3-235B at FP16, closed-source undisclosed
4. **golden_d saturation** — all models achieve 100% F1 (useful for hallucination only)
5. **English only** — all datasets are in English
6. **Single task** — medical chronology extraction only

## Reproducibility

- All code is version-controlled (Git)
- Dependencies pinned in `requirements.txt`
- Random seeds fixed (`seed=42` in bootstrap)
- Model configurations recorded in `models.json`
- Per-run metadata (tokens, latency, timestamps) saved in `metadata.json`
- Serving conditions documented (see METHODOLOGY.md §4.3.1)
- Results available in JSON (`golden_benchmark_aggregated.json`) and Markdown (`benchmark_presentation_v2.md`)

## Contributing

We welcome bug reports and feature requests via [GitHub Issues](https://github.com/superinsight/superinsight-ai-benchmark/issues). Pull requests are not accepted at this time — please open an issue first to discuss any proposed changes.

## License

Copyright 2026 Superinsight, Inc. Licensed under the [Apache License 2.0](LICENSE).
