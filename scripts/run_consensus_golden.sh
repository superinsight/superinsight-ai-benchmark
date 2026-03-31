#!/bin/bash
# Full consensus golden pipeline with multi-round support:
#   1. Synthesize source from consensus golden.json (skip if already exists)
#   2. Run all models against synthetic source (N rounds)
#   3. Evaluate + aggregate
#
# Usage:
#   ./run_consensus_golden.sh              # 3 rounds (default)
#   ./run_consensus_golden.sh 5            # 5 rounds
#   ./run_consensus_golden.sh 1            # single round
set -euo pipefail
cd "$(dirname "$0")/.."

source .env 2>/dev/null || true

NUM_ROUNDS=${1:-3}

GOLDEN_DIRS=(golden/golden_a golden/golden_b golden/golden_c)

MODELS=(
    "gemini:gemini-2.5-pro:gemini-2.5-pro"
    "gemini:gemini-2.5-flash:gemini-2.5-flash"
    "genai:gemini-3-flash-preview:gemini-3-flash"
    "genai:gemini-3.1-pro-preview:gemini-3.1-pro"
    "nebius::qwen3-235b"
    "openai:gpt-5.4:gpt-5.4"
    "anthropic:claude-opus-4-6:claude-opus-4.6"
)

# ── Step 1: Ensure synthetic sources exist ────────────────────────────────
echo ""
echo "============================================================"
echo "  Step 1: Check synthetic sources"
echo "============================================================"

for GOLDEN_DIR in "${GOLDEN_DIRS[@]}"; do
    GOLDEN_JSON="${GOLDEN_DIR}/golden.json"
    GOLDEN_NAME=$(basename "$GOLDEN_DIR")

    if [ ! -f "$GOLDEN_JSON" ]; then
        echo "  [skip] $GOLDEN_NAME — no golden.json"
        continue
    fi

    if [ -f "${GOLDEN_DIR}/synthetic_source.txt" ]; then
        SRC_SIZE=$(wc -c < "${GOLDEN_DIR}/synthetic_source.txt")
        echo "  [ok] $GOLDEN_NAME — synthetic_source exists (${SRC_SIZE} chars)"
    else
        echo "  --- Synthesizing $GOLDEN_NAME ---"
        python synthesize_golden.py --from-golden "$GOLDEN_JSON" 2>&1
    fi
done

# ── Step 2: Run all models × N rounds ────────────────────────────────────
echo ""
echo "============================================================"
echo "  Step 2: Run models (${NUM_ROUNDS} rounds × ${#MODELS[@]} models × ${#GOLDEN_DIRS[@]} golden)"
echo "============================================================"

for ROUND in $(seq 1 "$NUM_ROUNDS"); do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  ROUND ${ROUND}/${NUM_ROUNDS}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    for GOLDEN_DIR in "${GOLDEN_DIRS[@]}"; do
        GOLDEN_NAME=$(basename "$GOLDEN_DIR")
        SOURCE="${GOLDEN_DIR}/synthetic_source.txt"
        OUT_BASE="golden_outputs/round_${ROUND}/${GOLDEN_NAME}"

        if [ ! -f "$SOURCE" ]; then
            echo "  [skip] $GOLDEN_NAME — no synthetic_source.txt"
            continue
        fi

        for MODEL_SPEC in "${MODELS[@]}"; do
            IFS=':' read -r PROVIDER MODEL_ID LABEL <<< "$MODEL_SPEC"
            MODEL_OUT="${OUT_BASE}/${LABEL}"

            if [ -f "${MODEL_OUT}/output.md" ] && [ -s "${MODEL_OUT}/output.md" ]; then
                echo "  [skip] R${ROUND} ${GOLDEN_NAME}/${LABEL} — exists ($(wc -c < "${MODEL_OUT}/output.md") chars)"
                continue
            fi

            echo ""
            echo "  --- R${ROUND} ${GOLDEN_NAME} / ${LABEL} ---"
            python generate_outputs.py \
                -i instruction.txt \
                -s "$SOURCE" \
                -o "$OUT_BASE" \
                --model "${MODEL_SPEC}" \
                --sequential \
                2>&1 | tail -5
        done
    done
done

# ── Step 3: Evaluate + aggregate ─────────────────────────────────────────
echo ""
echo "============================================================"
echo "  Step 3: Evaluate all rounds"
echo "============================================================"

python evaluate_golden_only.py --rounds "$NUM_ROUNDS" 2>&1
