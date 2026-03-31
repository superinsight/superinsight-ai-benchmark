#!/bin/bash
# Synthesize golden datasets from all 3 source documents.
# Uses gemini-2.5-pro outputs as ground truth.
#
# Usage:
#   # Step 1: Synthesize (calls LLM to generate source docs)
#   bash run_golden_synthesis.sh synthesize
#
#   # Step 2: Generate model outputs against synthetic sources
#   bash run_golden_synthesis.sh generate
#
#   # Step 3: Evaluate all models
#   bash run_golden_synthesis.sh evaluate

set -euo pipefail
cd "$(dirname "$0")/.."

ACTION="${1:-help}"

# Ground truth outputs (from gemini-2.5-pro)
GT_A="outputs/mc_source_a_small_v2/gemini-2.5-pro/output.md"
GT_B="outputs/mc_source_b_small_v2/gemini-2.5-pro/output.md"
GT_C="outputs/mc_source_c_small_v2/gemini-2.5-pro/output.md"

case "$ACTION" in
  synthesize)
    echo "=== Synthesizing golden datasets ==="
    echo ""
    echo "--- Golden A (DDE style) ---"
    python synthesize_golden.py --output "$GT_A" --out-dir golden/golden_a --style dde
    echo ""
    echo "--- Golden B (Clinical Note style) ---"
    python synthesize_golden.py --output "$GT_B" --out-dir golden/golden_b --style clinical_note
    echo ""
    echo "--- Golden C (Mixed style) ---"
    python synthesize_golden.py --output "$GT_C" --out-dir golden/golden_c --style mixed
    echo ""
    echo "=== Done. Check golden/ directory. ==="
    ;;

  generate)
    echo "=== Generating model outputs against synthetic sources ==="
    for GOLDEN_DIR in golden/golden_a golden/golden_b golden/golden_c; do
      SOURCE="${GOLDEN_DIR}/synthetic_source.txt"
      OUT_BASE="golden_outputs/$(basename $GOLDEN_DIR)"
      if [ ! -f "$SOURCE" ]; then
        echo "Skipping $GOLDEN_DIR (no synthetic_source.txt)"
        continue
      fi
      echo ""
      echo "--- Generating for $GOLDEN_DIR ---"
      python generate_outputs.py \
        -i instruction.txt \
        -s "$SOURCE" \
        -o "$OUT_BASE"
    done
    echo ""
    echo "=== Done. Check golden_outputs/ directory. ==="
    ;;

  evaluate)
    echo "=== Evaluating all models against golden datasets ==="
    for GOLDEN_DIR in golden/golden_a golden/golden_b golden/golden_c; do
      GOLDEN_JSON="${GOLDEN_DIR}/golden.json"
      OUT_BASE="golden_outputs/$(basename $GOLDEN_DIR)"
      if [ ! -f "$GOLDEN_JSON" ]; then
        echo "Skipping $GOLDEN_DIR (no golden.json)"
        continue
      fi
      echo ""
      echo "--- Evaluating $GOLDEN_DIR ---"
      for MODEL_DIR in "$OUT_BASE"/*/; do
        MODEL_NAME=$(basename "$MODEL_DIR")
        OUTPUT_FILE="${MODEL_DIR}output.md"
        if [ ! -f "$OUTPUT_FILE" ]; then
          echo "  Skipping $MODEL_NAME (no output.md)"
          continue
        fi
        echo ""
        echo "  Model: $MODEL_NAME"
        python synthesize_golden.py --evaluate "$GOLDEN_JSON" "$OUTPUT_FILE"
      done
    done
    echo ""
    echo "=== Done. ==="
    ;;

  validate)
    echo "=== Validating golden datasets ==="
    for GOLDEN_DIR in golden/golden_a golden/golden_b golden/golden_c; do
      GOLDEN_JSON="${GOLDEN_DIR}/golden.json"
      if [ ! -f "$GOLDEN_JSON" ]; then
        echo "Skipping $GOLDEN_DIR (no golden.json)"
        continue
      fi
      echo ""
      echo "--- Validating $GOLDEN_DIR ---"
      python synthesize_golden.py --validate "$GOLDEN_JSON"
    done
    ;;

  help|*)
    echo "Usage: bash run_golden_synthesis.sh <action>"
    echo ""
    echo "Actions:"
    echo "  synthesize  - Generate synthetic source documents from ground truth"
    echo "  validate    - Check that synthetic sources contain all expected entries"
    echo "  generate    - Run models against synthetic sources"
    echo "  evaluate    - Compute Precision/Recall/F1 for all models"
    echo ""
    echo "Typical workflow:"
    echo "  1. bash run_golden_synthesis.sh synthesize"
    echo "  2. bash run_golden_synthesis.sh validate"
    echo "  3. bash run_golden_synthesis.sh generate"
    echo "  4. bash run_golden_synthesis.sh evaluate"
    ;;
esac
