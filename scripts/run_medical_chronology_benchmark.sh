#!/bin/bash
#
# Medical Chronology Benchmark — Full Suite
#
# Runs 6 models × 5 sizes × 3 sources = 90 generate runs + 15 comparisons
# For "full" size, only Gemini models are used (Qwen context too small for source_b/c)
#
# Usage:
#   chmod +x run_medical_chronology_benchmark.sh
#   ./run_medical_chronology_benchmark.sh           # run everything
#   ./run_medical_chronology_benchmark.sh --dry-run  # print commands without executing
#   ./run_medical_chronology_benchmark.sh --generate-only  # skip compare step
#   ./run_medical_chronology_benchmark.sh --compare-only   # skip generate step
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

INSTRUCTION="examples/medical_chronology_instruction.txt"
MODELS_ALL="models.json"
MAX_TOKENS=16384
TEMPERATURE=0.2

DRY_RUN=false
GENERATE_ONLY=false
COMPARE_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --dry-run)      DRY_RUN=true ;;
        --generate-only) GENERATE_ONLY=true ;;
        --compare-only)  COMPARE_ONLY=true ;;
    esac
done

# Models config for Gemini-only runs (full size where Qwen can't fit)
MODELS_GEMINI_ONLY="models_gemini_only.json"
if [ ! -f "$MODELS_GEMINI_ONLY" ]; then
    cat > "$MODELS_GEMINI_ONLY" << 'GEMINI_EOF'
[
  {"provider": "gemini", "model": "gemini-2.5-pro", "label": "gemini-2.5-pro"},
  {"provider": "gemini", "model": "gemini-2.5-flash", "label": "gemini-2.5-flash"},
  {"provider": "gemini", "model": "gemini-3-flash-preview", "label": "gemini-3-flash"},
  {"provider": "gemini", "model": "gemini-3.1-pro-preview", "label": "gemini-3.1-pro"}
]
GEMINI_EOF
fi

SOURCES=("source_a" "source_b" "source_c")
SIZES=("xs" "small" "medium" "large" "full")

# source_a_full = 231K tokens → Qwen can fit (256K context)
# source_b_full = 1M tokens → only Gemini
# source_c_full = 464K tokens → only Gemini
FULL_GEMINI_ONLY_SOURCES=("source_b" "source_c")

run_count=0
fail_count=0
skip_count=0

log() {
    echo ""
    echo "================================================================"
    echo "  $1"
    echo "================================================================"
}

run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] $*"
    else
        echo "[RUN] $*"
        if "$@"; then
            run_count=$((run_count + 1))
        else
            echo "[WARN] Command failed (exit $?), continuing..."
            fail_count=$((fail_count + 1))
        fi
    fi
}

# ── Phase 1: Generate outputs ──────────────────────────────────────────────

if [ "$COMPARE_ONLY" = false ]; then
    log "Phase 1: Generating model outputs"

    for src in "${SOURCES[@]}"; do
        for size in "${SIZES[@]}"; do
            source_file="examples/${src}_${size}.txt"

            if [ ! -f "$source_file" ]; then
                echo "[SKIP] $source_file does not exist"
                skip_count=$((skip_count + 1))
                continue
            fi

            output_dir="outputs/mc_${src}_${size}"

            # Determine which models to use
            use_gemini_only=false
            if [ "$size" = "full" ]; then
                for gs in "${FULL_GEMINI_ONLY_SOURCES[@]}"; do
                    if [ "$src" = "$gs" ]; then
                        use_gemini_only=true
                        break
                    fi
                done
            fi

            if [ "$use_gemini_only" = true ]; then
                models_config="$MODELS_GEMINI_ONLY"
                model_note="Gemini only"
            else
                models_config="$MODELS_ALL"
                model_note="all 6 models"
            fi

            log "Generate: ${src} / ${size} (${model_note}) → ${output_dir}"

            run_cmd python generate_outputs.py \
                -i "$INSTRUCTION" \
                -s "$source_file" \
                -o "$output_dir" \
                --models-config "$models_config" \
                --max-tokens "$MAX_TOKENS" \
                --temperature "$TEMPERATURE"
        done
    done

    echo ""
    echo "Phase 1 complete: $run_count succeeded, $fail_count failed, $skip_count skipped"
fi

# ── Phase 2: Run comparisons ──────────────────────────────────────────────

if [ "$GENERATE_ONLY" = false ]; then
    log "Phase 2: Running comparisons (with LLM Judge)"

    compare_count=0
    compare_fail=0

    for src in "${SOURCES[@]}"; do
        for size in "${SIZES[@]}"; do
            config_file="outputs/mc_${src}_${size}/comparison_config.json"

            if [ ! -f "$config_file" ]; then
                echo "[SKIP] $config_file does not exist"
                continue
            fi

            log "Compare: ${src} / ${size}"

            if [ "$DRY_RUN" = true ]; then
                echo "[DRY-RUN] python main.py --compare $config_file"
            else
                echo "[RUN] python main.py --compare $config_file"
                if python main.py --compare "$config_file"; then
                    compare_count=$((compare_count + 1))
                else
                    echo "[WARN] Comparison failed for ${src}/${size}, continuing..."
                    compare_fail=$((compare_fail + 1))
                fi
            fi
        done
    done

    echo ""
    echo "Phase 2 complete: $compare_count succeeded, $compare_fail failed"
fi

# ── Summary ───────────────────────────────────────────────────────────────

log "BENCHMARK COMPLETE"
echo ""
echo "Results are in:"
for src in "${SOURCES[@]}"; do
    for size in "${SIZES[@]}"; do
        result="outputs/mc_${src}_${size}/comparison_config_results.json"
        if [ -f "$result" ]; then
            echo "  ✅ $result"
        else
            echo "  ⬜ outputs/mc_${src}_${size}/ (no results yet)"
        fi
    done
done
echo ""
echo "To view a specific result:"
echo "  python main.py --compare outputs/mc_source_a_small/comparison_config.json"
