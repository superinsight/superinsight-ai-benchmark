# Quickstart Example

A minimal, self-contained example with **2 medical encounters** to demonstrate the benchmark pipeline end-to-end.

## Files

| File | Description |
|------|-------------|
| `source.txt` | Synthetic medical records (2 pages, 2 encounters + 1 admin noise) |
| `golden.json` | Ground truth: 2 must-extract entries with key fields |
| `sample_output.md` | Example LLM-generated chronology to evaluate |

## Try It

### 1. Evaluate extraction accuracy (no API key needed)

```bash
cd /path/to/superinsight-ai-benchmark

python -c "
from synthesize_golden import evaluate_against_golden
import json

result = evaluate_against_golden('examples/quickstart/golden.json', open('examples/quickstart/sample_output.md').read())
print(json.dumps(result, indent=2))
"
```

### 2. Run the formatting/completeness benchmark (no API key needed)

```bash
python main.py \
  --output examples/quickstart/sample_output.md \
  --instruction instruction.txt \
  --no-llm
```

### 3. Full benchmark with LLM judge (requires API key)

```bash
# Set up credentials (see env.example)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
export GCP_PROJECT_ID=your-project

python main.py \
  --output examples/quickstart/sample_output.md \
  --instruction instruction.txt \
  --source examples/quickstart/source.txt \
  --deep-check
```

## What to Expect

The sample output should score:
- **Extraction**: 100% F1 (both entries matched)
- **Formatting**: High (follows the required markdown structure)
- **Completeness**: High (key fields present)
- **Hallucination**: High (all claims have source citations)

Try modifying `sample_output.md` to see how scores change — for example, remove a citation, add a fabricated diagnosis, or delete an entry.
