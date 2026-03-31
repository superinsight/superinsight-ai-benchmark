#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# Incrementally add a new model to the benchmark.
#
# This script handles the full pipeline:
#   1. Generate outputs (3 rounds × 6 golden datasets)
#   2. F1 / deterministic evaluation (recalculates all — fast & deterministic)
#   3. Hallucination evaluation (incremental — only new model)
#   4. Bootstrap significance test (recalculates all — fast)
#   5. Leaderboard generation
#   6. Chart regeneration
#
# Usage:
#   ./add_model.sh <provider>:<model_id>:<label>
#
# Examples:
#   ./add_model.sh openai:gpt-6:gpt-6
#   ./add_model.sh gemini:gemini-4-pro:gemini-4-pro
#   ./add_model.sh nebius:MiniMaxAI/MiniMax-M3:minimax-m3
#   ./add_model.sh anthropic:claude-5:claude-5
#
# Prerequisites:
#   - .env file with API keys
#   - Existing golden datasets in golden/golden_{a..f}/
#   - models.json updated with the new model entry
#
# Notes:
#   - Output generation skips existing output.md files automatically
#   - Hallucination evaluation uses --incremental to skip already-evaluated combos
#   - Charts auto-discover new models (fallback colors/labels for unknown models)
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."

if [ $# -lt 1 ]; then
    echo "Usage: $0 <provider>:<model_id>:<label>"
    echo ""
    echo "Examples:"
    echo "  $0 openai:gpt-6:gpt-6"
    echo "  $0 gemini:gemini-4-pro:gemini-4-pro"
    echo "  $0 nebius:MiniMaxAI/MiniMax-M3:minimax-m3"
    exit 1
fi

MODEL_SPEC="$1"
IFS=':' read -r PROVIDER MODEL_ID LABEL <<< "$MODEL_SPEC"

if [ -z "$PROVIDER" ] || [ -z "$LABEL" ]; then
    echo "ERROR: Invalid model spec. Format: provider:model_id:label"
    exit 1
fi

ROUNDS=${2:-3}
HALLUC_ROUNDS=${3:-3}

GOLDEN_DIRS=(golden/golden_a golden/golden_b golden/golden_c golden/golden_d golden/golden_e golden/golden_f)

echo "================================================================"
echo "  Adding model: $LABEL"
echo "  Provider: $PROVIDER  |  Model ID: ${MODEL_ID:-'(default)'}"
echo "  Rounds: $ROUNDS  |  Hallucination Rounds: $HALLUC_ROUNDS"
echo "================================================================"
echo ""

# ── Step 1: Generate outputs ────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Step 1/6: Generate Outputs                             ║"
echo "╚══════════════════════════════════════════════════════════╝"

GENERATED=0
SKIPPED=0

for ROUND in $(seq 1 "$ROUNDS"); do
    for GOLDEN_DIR in "${GOLDEN_DIRS[@]}"; do
        GOLDEN_NAME=$(basename "$GOLDEN_DIR")
        SOURCE="${GOLDEN_DIR}/synthetic_source.txt"
        OUT_BASE="golden_outputs/round_${ROUND}/${GOLDEN_NAME}"
        MODEL_OUT="${OUT_BASE}/${LABEL}"

        if [ ! -f "$SOURCE" ]; then
            continue
        fi

        if [ -f "${MODEL_OUT}/output.md" ] && [ -s "${MODEL_OUT}/output.md" ]; then
            SIZE=$(wc -c < "${MODEL_OUT}/output.md")
            echo "  [skip] R${ROUND}/${GOLDEN_NAME}/${LABEL} — exists (${SIZE} bytes)"
            SKIPPED=$((SKIPPED + 1))
            continue
        fi

        echo "  [run]  R${ROUND}/${GOLDEN_NAME}/${LABEL}"

        MODEL_ARG="${PROVIDER}:${MODEL_ID}:${LABEL}"
        if [ -z "$MODEL_ID" ]; then
            MODEL_ARG="${PROVIDER}::${LABEL}"
        fi

        python generate_outputs.py \
            -i instruction.txt \
            -s "$SOURCE" \
            -o "$OUT_BASE" \
            --model "$MODEL_ARG" \
            --sequential \
            2>&1 | tail -5

        if [ -f "${MODEL_OUT}/output.md" ]; then
            SIZE=$(wc -c < "${MODEL_OUT}/output.md")
            echo "  ✓ R${ROUND}/${GOLDEN_NAME}/${LABEL} done (${SIZE} bytes)"
            GENERATED=$((GENERATED + 1))
        else
            echo "  ✗ R${ROUND}/${GOLDEN_NAME}/${LABEL} FAILED"
        fi
    done
done

echo ""
echo "  Output generation: ${GENERATED} generated, ${SKIPPED} skipped"
echo ""

# ── Step 2: F1 / Golden evaluation ──────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Step 2/6: F1 / Golden Evaluation                      ║"
echo "╚══════════════════════════════════════════════════════════╝"

python evaluate_golden_only.py --rounds "$ROUNDS"
echo ""

# ── Step 3: Deterministic evaluation ────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Step 3/6: Deterministic Evaluation                     ║"
echo "╚══════════════════════════════════════════════════════════╝"

python evaluate_deterministic.py --rounds "$ROUNDS" --semantic
echo ""

# ── Step 4: Hallucination evaluation (incremental) ──────────────────────────
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Step 4/6: Hallucination Evaluation (incremental)       ║"
echo "╚══════════════════════════════════════════════════════════╝"

python evaluate_hallucination.py \
    --rounds "$HALLUC_ROUNDS" \
    --judges all \
    --models "$LABEL" \
    --incremental
echo ""

# ── Step 5: Bootstrap significance test ─────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Step 5/6: Bootstrap Significance Test                  ║"
echo "╚══════════════════════════════════════════════════════════╝"

python evaluate_bootstrap.py
echo ""

# ── Step 6: Leaderboard + Charts ────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Step 6/6: Leaderboard + Charts                         ║"
echo "╚══════════════════════════════════════════════════════════╝"

python generate_leaderboard.py
python generate_charts.py
echo ""

# ── Summary ─────────────────────────────────────────────────────────────────
echo "================================================================"
echo "  ✅ Model '$LABEL' added successfully!"
echo ""
echo "  Outputs:"
echo "    golden_outputs/golden_benchmark_aggregated.json  (F1 scores)"
echo "    golden_outputs/deterministic_results.json        (formatting/citation)"
echo "    golden_outputs/hallucination_results.json        (hallucination)"
echo "    golden_outputs/bootstrap_results.json            (significance)"
echo "    golden_outputs/leaderboard.json                  (ranked leaderboard)"
echo "    charts/                                          (all visualizations)"
echo ""
echo "  Next steps:"
echo "    1. Update models.json if not already done"
echo "    2. Update benchmark_presentation_v2.md tables"
echo "    3. Review charts/ for the new model's results"
echo "================================================================"
