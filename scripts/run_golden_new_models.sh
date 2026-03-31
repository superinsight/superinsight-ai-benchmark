#!/bin/bash
# Run NEW models (gpt-5.4-pro, gpt-5.4-mini, claude-opus-4.5, minimax-m2.5)
# against all golden synthetic sources for 3 rounds.
#
# Usage:
#   ./run_golden_new_models.sh              # all 3 rounds
#   ./run_golden_new_models.sh 1            # round 1 only
#   ./run_golden_new_models.sh 1 3          # rounds 1 to 3
set -euo pipefail
cd "$(dirname "$0")/.."

START_ROUND=${1:-1}
END_ROUND=${2:-3}

NEW_MODELS=(
    "openai:gpt-5.4-pro:gpt-5.4-pro"
    "openai:gpt-5.4-mini:gpt-5.4-mini"
    "anthropic:claude-opus-4-5-20251101:claude-opus-4.5"
    "nebius:MiniMaxAI/MiniMax-M2.5:minimax-m2.5"
)

GOLDEN_DIRS=(golden/golden_a golden/golden_b golden/golden_c)

for ROUND in $(seq "$START_ROUND" "$END_ROUND"); do
    echo ""
    echo "################################################################"
    echo "  ROUND $ROUND"
    echo "################################################################"

    for GOLDEN_DIR in "${GOLDEN_DIRS[@]}"; do
        GOLDEN_NAME=$(basename "$GOLDEN_DIR")
        SOURCE="${GOLDEN_DIR}/synthetic_source.txt"
        OUT_BASE="golden_outputs/round_${ROUND}/${GOLDEN_NAME}"

        if [ ! -f "$SOURCE" ]; then
            echo "Skipping $GOLDEN_DIR (no synthetic_source.txt)"
            continue
        fi

        echo ""
        echo "============================================================"
        echo "  Round $ROUND / $GOLDEN_NAME"
        echo "============================================================"

        for MODEL_SPEC in "${NEW_MODELS[@]}"; do
            IFS=':' read -r PROVIDER MODEL_ID LABEL <<< "$MODEL_SPEC"
            MODEL_OUT="${OUT_BASE}/${LABEL}"

            if [ -f "${MODEL_OUT}/output.md" ] && [ -s "${MODEL_OUT}/output.md" ]; then
                SIZE=$(wc -c < "${MODEL_OUT}/output.md")
                echo "  [skip] $LABEL — output already exists (${SIZE} bytes)"
                continue
            fi

            echo ""
            echo "  --- $LABEL ---"
            python generate_outputs.py \
                -i instruction.txt \
                -s "$SOURCE" \
                -o "$OUT_BASE" \
                --model "${PROVIDER}:${MODEL_ID}:${LABEL}" \
                --sequential \
                2>&1 | tail -10

            if [ -f "${MODEL_OUT}/output.md" ]; then
                SIZE=$(wc -c < "${MODEL_OUT}/output.md")
                echo "  ✓ $LABEL done (${SIZE} bytes)"
            else
                echo "  ✗ $LABEL FAILED — no output.md generated"
            fi
        done
    done
done

echo ""
echo "################################################################"
echo "  ALL ROUNDS COMPLETE"
echo "  Now run:"
echo "    python evaluate_golden_only.py --rounds $END_ROUND"
echo "    python evaluate_deterministic.py --rounds $END_ROUND"
echo "    python generate_charts.py"
echo "################################################################"
