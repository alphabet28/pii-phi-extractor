# Project Structure Overview

This document explains the architecture and design of the PII/PHI extraction pipeline.

## Directory Structure

```
pii-phi-extraction/
├── extractors/                  # Stage 1: File extraction modules
│   ├── __init__.py
│   └── file_extractor.py       # Main extraction engine
│
├── detectors/                   # Stage 2: PII/PHI detection modules
│   ├── __init__.py
│   └── pii_phi_detector.py     # Presidio-based detection engine
│
├── sample_docs/                 # Test documents for validation
│   ├── patient_record_1.txt
│   ├── employee_data.txt
│   ├── clean_document.txt
│   └── medical_report.txt
│
├── output/                      # Generated results (created at runtime)
│   ├── results.json            # Full per-document results
│   └── summary_report.json     # Aggregate statistics
│
├── pipeline.py                  # Main orchestrator (entry point)
├── verify_setup.py             # Setup verification script
├── examples.py                 # Advanced usage examples
├── requirements.txt            # Python dependencies
├── README.md                   # Full documentation
├── QUICKSTART.md              # Getting started guide
├── PROJECT_STRUCTURE.md       # This file
└── .gitignore                 # Git exclusions
```

## Module Architecture

### 1. File Extractor (Stage 1)

**File**: `extractors/file_extractor.py`

**Purpose**: Normalize text extraction across diverse file formats without external JVM services.

**Key Components**:

- `FileExtractor` class
  - Main orchestrator that routes files to format-specific handlers
  - `extract(filepath)` → `ExtractionResult`

- Format-specific handlers:
  - `_extract_text()` — Plain text, Markdown
  - `_extract_docx()` — Microsoft Word with table support
  - `_extract_xlsx()` — Excel spreadsheets (all sheets, data-only mode)
  - `_extract_pdf()` — PDFs with scanned page detection
  - `_extract_eml()` — Email files with MIME tree parsing
  - `_extract_msg()` — Outlook MSG files

- Special logic:
  - **PDF scanning detection**: Flags PDFs with no extractable text as `needs_ocr`
  - **Email attachments**: Recursively extracts nested files with supported extensions
  - **Table extraction**: Special handling for DOCX tables and PDF embedded tables

**Output** (`ExtractionResult`):
```python
{
    "filename": str,
    "filepath": str,
    "filetype": str,
    "text": str,                    # Concatenated extracted text
    "metadata": dict,               # Format-specific metadata
    "extraction_status": str,       # "success" | "error" | "empty" | "needs_ocr"
    "error": str | None,
    "attachment_extractions": list  # For email attachments
}
```

### 2. PII/PHI Detector (Stage 2)

**File**: `detectors/pii_phi_detector.py`

**Purpose**: Fast triage using Microsoft Presidio with custom regex patterns and entity classification.

**Key Components**:

- `PiiPhiDetector` class
  - Initializes Presidio with blank spaCy model (no network/auto-download)
  - `triage(text)` → `TriageResult` (fast pass on all documents)
  - `extract_structured(text)` → grouped entities (for flagged documents)

- Custom pattern recognizers:
  - US_SSN, PHONE_NUMBER, CREDIT_CARD, PASSPORT_NUMBER
  - MEDICAL_RECORD_NUMBER, HEALTH_INSURANCE_ID
  - ICD10_CODE, DATE_OF_BIRTH, US_BANK_NUMBER, IP_ADDRESS

- Entity classification:
  - **PII**: SSN, email, phone, credit card, passport, bank, IP, names
  - **PHI**: MRN, insurance ID, ICD-10, date of birth

**Output** (`TriageResult`):
```python
{
    "pii_phi_matches": [
        {
            "entity_type": str,
            "label": str,           # Human-readable
            "category": "PII" | "PHI",
            "value": str,           # Matched text
            "start": int,
            "end": int,
            "confidence": float     # 0.0 - 1.0
        }
    ],
    "match_count": int,
    "contains_pii": bool,
    "contains_phi": bool,
    "flagged_for_review": bool
}
```

### 3. Pipeline Orchestrator

**File**: `pipeline.py`

**Purpose**: Coordinates all stages, manages I/O, and generates reports.

**Key Components**:

- `PiiPhiPipeline` class
  - `process_directory(directory)` — Main entry point
  - Walks directory recursively, collects supported files
  - For each file: extract → check status → triage (if applicable)
  - Segregates results: flagged / clean / error / OCR queue
  - Generates `results.json` and `summary_report.json`
  - Prints human-readable summary to stdout

**Workflow**:
1. Walk directory recursively → list of files
2. For each file:
   - Stage 1: Extract text (`FileExtractor.extract()`)
   - Check extraction status:
     - `needs_ocr` → add to OCR queue, skip triage
     - `error` → log error, include in results
     - `empty` → mark clean, skip triage
     - `success` → proceed to triage
   - Stage 2: Triage document (`PiiPhiDetector.triage()`)
   - Merge extraction + triage results
   - Categorize: flagged vs. clean
3. After all files:
   - Generate `results.json` (all documents)
   - Generate `summary_report.json` (aggregate stats)
   - Print human-readable summary

## Data Flow

```
Input Directory
    ↓
FileExtractor (Stage 1)
    ├─→ Extraction fails → error_documents
    ├─→ File empty → clean_documents
    ├─→ PDF scanned → ocr_queue
    └─→ Success → proceed to Stage 2
        ↓
    PiiPhiDetector (Stage 2)
        ├─→ No matches → clean_documents
        └─→ Matches found → flagged_documents
            ↓
    Merge Results
        ├─→ results.json (all documents)
        ├─→ summary_report.json (aggregate stats)
        └─→ stdout (human summary)
```

## Confidence Thresholds

The detector uses a **two-tier confidence system**:

1. **Entity-specific scores** (when match is detected):
   - High: 0.85-0.90 (SSN, Passport, MRN, DOB)
   - Medium: 0.70-0.80 (Phone, Credit Card, Insurance ID)
   - Lower: 0.60 (ICD-10 — pattern overlap)

2. **Triage threshold**: 0.55
   - Matches below 0.55 are discarded at triage stage
   - Matches ≥ 0.55 included in results
   - Customizable in `detectors/pii_phi_detector.py`

## Performance Characteristics

**Per-file processing** (single-threaded, typical speeds):

| Document Type | Size | Time | Status |
|---|---|---|---|
| Plain text | 10 KB | 10 ms | extract + triage |
| Word doc | 500 KB | 50 ms | includes table parsing |
| Excel sheet | 1 MB | 100 ms | all sheets extracted |
| Small PDF | 5 MB | 200 ms | text + tables |
| Large PDF | 20 MB | 1 s | full page scan |

**Throughput** (single-threaded):
- Small documents: 1000+ files/min
- Medium documents: 100-300 files/min
- Large documents: 50-100 files/min

**Memory footprint**:
- Base: ~100 MB (Presidio + spaCy)
- Per-file: 10-50 MB (varies by format)
- With 8-core multiprocessing: ~800 MB - 1.2 GB

## Configuration Points

### Confidence Threshold
File: `detectors/pii_phi_detector.py`, line ~65
```python
CONFIDENCE_THRESHOLD = 0.55
```
- Lower = more detections, higher false positive rate
- Higher = fewer detections, higher precision

### Custom Entity Patterns
File: `detectors/pii_phi_detector.py`, method `_add_custom_recognizers()`
```python
PatternRecognizer(
    supported_entity="YOUR_ENTITY",
    patterns=[re.compile(r'your_regex')],
    score=0.75
)
```

### Logging Level
File: `pipeline.py`, line ~28
```python
logging.basicConfig(level=logging.INFO)  # DEBUG, INFO, WARNING, ERROR
```

### Attachment Processing Settings
File: `extractors/file_extractor.py`, lines ~40-42
```python
MAX_ATTACHMENT_DEPTH = 3          # Nesting depth limit
ATTACHMENT_SIZE_LIMIT = 50 * 1024 * 1024  # 50 MB
```

## Scalability Patterns

### For Millions of Documents

1. **Multiprocessing** (4-8 processes on single machine):
   ```python
   from concurrent.futures import ProcessPoolExecutor
   with ProcessPoolExecutor(max_workers=8) as executor:
       futures = [executor.submit(process_file, f) for f in files]
   ```

2. **Distributed task queue** (Celery + Redis):
   ```python
   @celery_app.task
   def process_file(filepath):
       # extraction + triage in separate worker
   ```

3. **Cloud scale** (Kubernetes, Apache Spark):
   - Stateless workers process files from central queue
   - Results written to distributed database (Elasticsearch, DuckDB)

## Future Extensions

### LLM-Based Extraction (Stage 3)
For higher precision and contextual PII/PHI:
- Send flagged documents to Ollama + LLaMA 3
- Structured extraction with context-aware handling

### OCR Processing
For scanned PDFs in `needs_ocr` queue:
- PaddleOCR (faster, GPU-optimized)
- Tesseract (slower, CPU-only)
- Re-enter pipeline at Stage 2 after OCR

### Redaction Engine
- Automatically redact detected PII/PHI
- Output cleaned document versions
- Track what was redacted in audit log

### Elasticsearch Integration
- Index all results for fast querying
- Reviewer dashboard for flagged documents
- Full-text search across extracted content

## Testing & Validation

**Sample documents** provided in `sample_docs/`:
- `patient_record_1.txt` — Contains PII + PHI
- `employee_data.txt` — Contains identity/financial PII
- `medical_report.txt` — Contains medical PHI
- `clean_document.txt` — No PII/PHI

**Test command**:
```bash
python pipeline.py sample_docs/
```

Expected results:
- 4 documents processed
- 3 flagged (patient, employee, medical)
- 1 clean
- ~28 total matches detected

## Dependencies & Versions

See `requirements.txt` for pinned versions. Key dependencies:

- **presidio-analyzer** ≥0.7.1 — PII/PHI detection engine
- **spacy** ≥3.5.0 — NLP backbone (blank model)
- **python-docx** ≥0.8.11 — Word document parsing
- **openpyxl** ≥3.10.0 — Excel parsing
- **pdfplumber** ≥0.9.0 — PDF extraction
- **extract-msg** ≥0.46.0 — Outlook MSG parsing
- **beautifulsoup4** ≥4.11.0 — HTML parsing

## Known Limitations

1. **No OCR in baseline** — Scanned PDFs flagged, not processed
2. **NER limited** — Uses blank spaCy model; en_core_web_lg requires network
3. **No fuzzy matching** — Regex patterns only; LLM pass planned for Stage 3
4. **Single-threaded by default** — Designed for easy scaling via ProcessPoolExecutor
5. **No redaction** — Detects PII/PHI but doesn't remove it; planned for future

## Debugging

Enable debug logging:
```bash
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from pipeline import PiiPhiPipeline
p = PiiPhiPipeline()
p.process_directory('sample_docs/')
"
```

Check specific file:
```python
from extractors.file_extractor import FileExtractor
result = FileExtractor().extract('path/to/file')
print(result.to_dict())
```

Test detector alone:
```python
from detectors.pii_phi_detector import PiiPhiDetector
detector = PiiPhiDetector()
triage = detector.triage("SSN: 123-45-6789")
print(f"Matches: {triage.match_count}")
```
