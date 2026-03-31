#!/bin/bash
# Run ALL 12 models against golden D/E/F synthetic sources for 3 rounds.
#
# Usage:
#   ./run_golden_def.sh              # all 3 rounds
#   ./run_golden_def.sh 1            # round 1 only
#   ./run_golden_def.sh 1 3          # rounds 1 to 3
set -euo pipefail
cd "$(dirname "$0")/.."

START_ROUND=${1:-1}
END_ROUND=${2:-3}

ALL_MODELS=(
    "gemini:gemini-2.5-pro:gemini-2.5-pro"
    "gemini:gemini-2.5-flash:gemini-2.5-flash"
    "genai:gemini-3-flash-preview:gemini-3-flash"
    "genai:gemini-3.1-pro-preview:gemini-3.1-pro"
    "nebius::qwen3-235b"
    "openai:gpt-5.4:gpt-5.4"
    "anthropic:claude-opus-4-6:claude-opus-4.6"
    "openai:gpt-5.4-pro:gpt-5.4-pro"
    "openai:gpt-5.4-mini:gpt-5.4-mini"
    "anthropic:claude-opus-4-5-20251101:claude-opus-4.5"
    "nebius:MiniMaxAI/MiniMax-M2.5:minimax-m2.5"
)

GOLDEN_DIRS=(golden/golden_d golden/golden_e golden/golden_f)

TOTAL_MODELS=${#ALL_MODELS[@]}
TOTAL_GOLDENS=${#GOLDEN_DIRS[@]}
TOTAL_ROUNDS=$((END_ROUND - START_ROUND + 1))
TOTAL_JOBS=$((TOTAL_MODELS * TOTAL_GOLDENS * TOTAL_ROUNDS))
DONE=0
SKIPPED=0
FAILED=0

echo "================================================================"
echo "  Golden D/E/F Benchmark Run"
echo "  Models: $TOTAL_MODELS | Datasets: $TOTAL_GOLDENS | Rounds: $TOTAL_ROUNDS"
echo "  Total jobs: $TOTAL_JOBS"
echo "================================================================"

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

        for MODEL_SPEC in "${ALL_MODELS[@]}"; do
            IFS=':' read -r PROVIDER MODEL_ID LABEL <<< "$MODEL_SPEC"
            MODEL_OUT="${OUT_BASE}/${LABEL}"

            if [ -f "${MODEL_OUT}/output.md" ] && [ -s "${MODEL_OUT}/output.md" ]; then
                SIZE=$(wc -c < "${MODEL_OUT}/output.md")
                echo "  [skip] $LABEL — output already exists (${SIZE} bytes)"
                SKIPPED=$((SKIPPED + 1))
                DONE=$((DONE + 1))
                continue
            fi

            echo ""
            echo "  --- $LABEL ($((DONE + 1))/$TOTAL_JOBS) ---"

            MODEL_ARG="${PROVIDER}:${MODEL_ID}:${LABEL}"
            if [ -z "$MODEL_ID" ]; then
                MODEL_ARG="${PROVIDER}::${LABEL}"
            fi

            if python generate_outputs.py \
                -i instruction.txt \
                -s "$SOURCE" \
                -o "$OUT_BASE" \
                --model "$MODEL_ARG" \
                --sequential \
                2>&1 | tail -5; then

                if [ -f "${MODEL_OUT}/output.md" ]; then
                    SIZE=$(wc -c < "${MODEL_OUT}/output.md")
                    echo "  ✓ $LABEL done (${SIZE} bytes)"
                else
                    echo "  ✗ $LABEL FAILED — no output.md generated"
                    FAILED=$((FAILED + 1))
                fi
            else
                echo "  ✗ $LABEL FAILED — command error"
                FAILED=$((FAILED + 1))
            fi

            DONE=$((DONE + 1))
        done
    done
done

echo ""
echo "################################################################"
echo "  ALL ROUNDS COMPLETE"
echo "  Done: $DONE | Skipped: $SKIPPED | Failed: $FAILED"
echo ""
echo "  Now run:"
echo "    python evaluate_golden_only.py --rounds $END_ROUND"
echo "    python evaluate_deterministic.py --rounds $END_ROUND --semantic"
echo "    python evaluate_hallucination.py --rounds 1 --judges all"
echo "    python generate_charts.py"
echo "################################################################"
