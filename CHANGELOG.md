# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-03-31

Initial public release.

### Added
- **11-model benchmark** across 6 golden datasets and 3 independent rounds
- **6 evaluation dimensions**: Extraction Accuracy (F1), Date Coverage, Formatting, Chronological Order, Content Fidelity (ROUGE-L + Semantic), Hallucination (multi-judge LLM ensemble)
- Multi-phase matching with Hungarian algorithm and fuzzy facility matching
- Statistical rigor: bootstrap confidence intervals, pairwise significance, Elo ratings
- LLM-as-Judge hallucination detection with 3-judge ensemble and citation verification
- Pre-generated outputs for all 198 model × dataset × round combinations
- Quickstart example (`examples/quickstart/`) for hands-on evaluation
- Deterministic evaluation mode (`--no-llm`) for zero-cost benchmarking
- Multi-provider support: OpenAI, Anthropic, Google (Gemini/Vertex AI), Nebius
- Comprehensive methodology documentation (`METHODOLOGY.md`)
- 30-slide Marp presentation (`benchmark_presentation_v2.md`)
