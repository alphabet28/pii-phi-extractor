# Quick Start Guide

Get the PII/PHI extraction pipeline running in 5 minutes.

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Verify Setup

```bash
python verify_setup.py
```

Expected output:
```
✓ Python 3.9 (OK)
✓ presidio-analyzer installed
✓ presidio-anonymizer installed
...
✓ All dependencies installed!
```

## Step 3: Test with Sample Documents

```bash
python pipeline.py sample_docs/
```

You should see:
```
2024-03-15 14:32:00 - __main__ - INFO - Starting PII/PHI extraction pipeline on: sample_docs
2024-03-15 14:32:00 - __main__ - INFO - Found 4 supported files to process
2024-03-15 14:32:01 - __main__ - INFO - [1/4] Processing: sample_docs\patient_record_1.txt
  → FLAGGED: 8 matches found
...

======================================================================
PII/PHI EXTRACTION PIPELINE - SUMMARY REPORT
======================================================================
Total documents processed: 4
  ✓ Flagged for review: 3
  ✓ Clean (no PII/PHI): 1
  ✗ Errors: 0
  ⚠ Need OCR: 0

PII/PHI Detection Summary:
  Documents with PII: 2
  Documents with PHI: 3
  Total entities detected: 28

Entity Breakdown:
  Medical Record Number: 4
  Email Address: 4
  Phone Number: 4
  ...
```

## Step 4: Check Results

Two files are created in `output/`:

### results.json
Full details for each document with all detected entities:

```bash
cat output/results.json | head -100
```

### summary_report.json
Aggregate statistics:

```bash
python -m json.tool output/summary_report.json
```

## Step 5: Process Your Documents

```bash
python pipeline.py /path/to/your/documents --output /path/to/output
```

## Common Use Cases

### Process a single directory
```bash
python pipeline.py /data/breach_investigation
```

### Process and save to custom location
```bash
python pipeline.py /data/documents --output /results/analysis_2024
```

### Process from current directory
```bash
python pipeline.py .
```

## Understanding Results

Each document in `results.json` has:

```json
{
  "filename": "document.txt",
  "filetype": ".txt",
  "extraction_status": "success",
  "flagged_for_review": true,
  "match_count": 5,
  "contains_pii": true,
  "contains_phi": true,
  "pii_phi_matches": [
    {
      "entity_type": "US_SSN",
      "label": "Social Security Number",
      "category": "PII",
      "value": "123-45-6789",
      "confidence": 0.85
    },
    ...
  ]
}
```

## Key Fields

- `extraction_status`: 
  - `"success"` — file extracted successfully
  - `"error"` — extraction failed (check `error` field)
  - `"needs_ocr"` — PDF is scanned; needs OCR processing
  - `"empty"` — file has no text content

- `flagged_for_review`: `true` if any PII/PHI found

- `contains_pii`: Personal Identifiable Information (SSN, email, phone, credit card, etc.)

- `contains_phi`: Protected Health Information (MRN, insurance ID, diagnosis codes, DOB)

- `confidence`: Score 0.0-1.0 (higher = more confident match)

## Summary Report

`summary_report.json` provides:

```json
{
  "total_documents": 1000,
  "flagged_documents": 342,        // Need human review
  "clean_documents": 658,          // No PII/PHI
  "error_documents": 0,
  "needs_ocr": 5,                  // Require OCR processing
  "total_matches": 1247,
  "entity_breakdown": {
    "EMAIL_ADDRESS": 432,
    "MEDICAL_RECORD_NUMBER": 156,
    ...
  },
  "by_filetype": {
    ".txt": {"total": 600, "flagged": 200},
    ".pdf": {"total": 300, "flagged": 120},
    ".xlsx": {"total": 100, "flagged": 22}
  }
}
```

## Troubleshooting

### "presidio-analyzer not found"
```bash
pip install presidio-analyzer presidio-anonymizer
```

### Pipeline runs but no detections
- Check confidence threshold in `detectors/pii_phi_detector.py` (default: 0.55)
- Lower the threshold to catch more entities (higher false positive rate)

### "needs_ocr" documents in results
These PDFs are scanned (image-based). To extract text:

1. Install OCR tool:
   ```bash
   pip install paddleocr
   ```

2. Process scanned PDFs separately (feature for future implementation)

### Slow processing
For large directories, consider:
- Using multiprocessing (see README.md advanced section)
- Processing in batches
- Pre-filtering by file type

## Next Steps

1. **Read the full README.md** for advanced configuration
2. **Configure custom patterns** for your specific document types
3. **Scale up** using multiprocessing for millions of documents
4. **Integrate with downstream tools** (Elasticsearch, data warehouse, etc.)

## Example: Processing a Data Breach Corpus

```bash
# Stage 1: Initial triage
python pipeline.py /mnt/breach_data/all_files --output /results/initial_scan

# Stage 2: Analyze results
cat /results/initial_scan/summary_report.json

# Stage 3: Export flagged documents for detailed review
python -c "
import json
with open('/results/initial_scan/results.json') as f:
    results = json.load(f)
flagged = [r for r in results if r['flagged_for_review']]
print(f'Documents flagged for review: {len(flagged)}')
for doc in flagged[:10]:  # Show first 10
    print(f'  - {doc[\"filename\"]}: {doc[\"match_count\"]} matches')
"
```

## Support

For detailed information:
- See **README.md** for full documentation
- Check **pipeline.py** for CLI options
- Review source code for customization examples
