#!/bin/bash
# Run all models against all golden synthetic sources, then evaluate.
set -euo pipefail
cd "$(dirname "$0")/.."

MODELS=(
    "gemini:gemini-2.5-pro:gemini-2.5-pro"
    "gemini:gemini-2.5-flash:gemini-2.5-flash"
    "genai:gemini-3-flash-preview:gemini-3-flash"
    "genai:gemini-3.1-pro-preview:gemini-3.1-pro"
    "nebius::qwen3-235b"
)

for GOLDEN_DIR in golden/golden_a golden/golden_b golden/golden_c; do
    GOLDEN_NAME=$(basename "$GOLDEN_DIR")
    SOURCE="${GOLDEN_DIR}/synthetic_source.txt"
    OUT_BASE="golden_outputs/${GOLDEN_NAME}"

    if [ ! -f "$SOURCE" ]; then
        echo "Skipping $GOLDEN_DIR (no synthetic_source.txt)"
        continue
    fi

    echo ""
    echo "============================================================"
    echo "  $GOLDEN_NAME — generating outputs"
    echo "============================================================"

    for MODEL_SPEC in "${MODELS[@]}"; do
        IFS=':' read -r PROVIDER MODEL_ID LABEL <<< "$MODEL_SPEC"
        MODEL_OUT="${OUT_BASE}/${LABEL}"

        if [ -f "${MODEL_OUT}/output.md" ] && [ -s "${MODEL_OUT}/output.md" ]; then
            echo "  [skip] $LABEL — output already exists ($(wc -c < "${MODEL_OUT}/output.md") chars)"
            continue
        fi

        echo ""
        echo "  --- $LABEL ---"
        python generate_outputs.py \
            -i instruction.txt \
            -s "$SOURCE" \
            -o "$OUT_BASE" \
            --model "${MODEL_SPEC}" \
            --sequential \
            2>&1 | tail -5
    done
done

echo ""
echo "============================================================"
echo "  EVALUATION"
echo "============================================================"

python -c "
import json, os, sys
from pathlib import Path
sys.path.insert(0, '.')
from synthesize_golden import evaluate_against_golden

all_results = {}

for golden_name in ['golden_a', 'golden_b', 'golden_c']:
    golden_path = f'golden/{golden_name}/golden.json'
    output_dir = f'golden_outputs/{golden_name}'
    with open(golden_path) as f:
        g = json.load(f)
    must = sum(1 for e in g['entries'] if e.get('must_extract') is True)
    may = sum(1 for e in g['entries'] if e.get('must_extract') == 'may_extract')
    noise = sum(1 for e in g['entries'] if e.get('must_extract') is False)
    print(f'\n--- {golden_name} (style={g[\"style\"]}, must={must}, may={may}, noise={noise}) ---')
    print(f'  {\"Model\":25s}  {\"Prec\":>6s}  {\"Recall\":>6s}  {\"F1\":>6s}  {\"FI\":>6s}  {\"TP\":>3s}  {\"FP\":>3s}  {\"FN\":>3s}  {\"May\":>3s}  {\"#\":>3s}')
    results = {}
    for model in sorted(os.listdir(output_dir)):
        output_file = os.path.join(output_dir, model, 'output.md')
        if not os.path.isfile(output_file): continue
        md = Path(output_file).read_text(encoding='utf-8')
        if not md.strip():
            print(f'  {model:25s}  (empty output)')
            continue
        r = evaluate_against_golden(golden_path, md)
        results[model] = r
        may_m = r.get('may_extract_matched', 0)
        print(f'  {model:25s}  {r[\"precision\"]:5.1%}  {r[\"recall\"]:5.1%}  {r[\"f1\"]:5.1%}  {r[\"false_inclusion_rate\"]:5.1%}  {r[\"true_positives\"]:3d}  {r[\"false_positives\"]:3d}  {r[\"false_negatives\"]:3d}  {may_m:3d}  {r[\"total_model_entries\"]:3d}')
    all_results[golden_name] = results

# Summary
print(f'\n=== CROSS-DATASET SUMMARY (F1) ===')
models_seen = set()
for res in all_results.values(): models_seen.update(res.keys())
print(f'  {\"Model\":25s}  {\"golden_a\":>9s}  {\"golden_b\":>9s}  {\"golden_c\":>9s}  {\"AVG\":>9s}')
for model in sorted(models_seen):
    f1s = []
    print(f'  {model:25s}', end='')
    for gn in ['golden_a', 'golden_b', 'golden_c']:
        r = all_results.get(gn, {}).get(model)
        if r:
            f1s.append(r['f1'])
            print(f'  {r[\"f1\"]:8.1%}', end='')
        else:
            print(f'  {\"—\":>9s}', end='')
    avg = sum(f1s)/len(f1s) if f1s else 0
    print(f'  {avg:8.1%}')

with open('golden_outputs/golden_benchmark_results.json', 'w') as f:
    json.dump(all_results, f, indent=2)
print(f'\nSaved: golden_outputs/golden_benchmark_results.json')
"
