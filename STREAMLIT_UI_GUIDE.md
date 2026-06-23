# 🎨 Streamlit UI Guide

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Streamlit App
```bash
streamlit run streamlit_app.py
```

The app will open in your default browser at `http://localhost:8501`

---

## Features

### 📤 Tab 1: Upload & Process
- **Upload multiple files** at once (drag & drop or click to browse)
- **Supported formats:** .txt, .md, .docx, .xlsx, .pdf, .eml, .msg
- **Real-time processing** with progress bar
- **Immediate results** showing all detected entities
- **Detailed view** with text preview and entity list

**How to use:**
1. Select files to upload
2. Click "🚀 Process Files"
3. Wait for processing to complete
4. Expand each file to see detailed results

### 📊 Tab 2: Results
- **Summary statistics** at a glance
- **Document summary table** with entity counts by type
- **Export options:**
  - Download as JSON (detailed results)
  - Download as CSV (summary table)

**Columns shown:**
- Filename
- File Type
- Total Entities Found
- PII Count
- PHI Count
- Processing Status

### 📈 Tab 3: Analytics
- **Entity type distribution** (bar chart)
- **PII vs PHI breakdown** (pie chart)
- **Confidence score distribution** (histogram)
- **File type analysis** (detailed statistics)

**Useful for:**
- Understanding which entity types appear most frequently
- Identifying high-confidence vs low-confidence detections
- Analyzing by file type

### 📚 Tab 4: Batch History
- **Session history** of all processed files
- **Expandable details** for each file
- **Entity breakdown** with confidence scores
- **Clear history** button to reset

---

## Configuration (Sidebar)

### Confidence Threshold
Adjust the minimum confidence score (0.0 - 1.0) for entity detection:
- **0.55** (default): Balanced sensitivity
- **0.70+**: High confidence, fewer false positives
- **0.30+**: High sensitivity, may include lower confidence matches

Changes apply to **future processing**, not retroactively.

---

## Color Coding

### Results Highlighting
- 🔴 **Red backgrounds** = PII (Personally Identifiable Information)
- 🟢 **Green backgrounds** = PHI (Protected Health Information)

### Confidence Indicators
- 🔴 **Red** = High confidence (>0.80)
- 🟡 **Yellow** = Medium confidence (0.60-0.80)
- 🟢 **Green** = Lower confidence (<0.60)

---

## Detected Entity Types

### PII Entities (8 types)
| Entity | Example | Confidence |
|--------|---------|-----------|
| US_SSN | 123-45-6789 | 0.85 |
| PHONE_NUMBER | (555) 123-4567 | 0.70 |
| CREDIT_CARD | 4111 1111 1111 1111 | 0.75 |
| PASSPORT_NUMBER | 123456789 | 0.85 |
| US_BANK_NUMBER | 00219745 | 0.80 |
| IP_ADDRESS | 192.168.1.1 | 0.70 |
| DATE_OF_BIRTH | 01/15/1980 | 0.90 |

### PHI Entities (5 types)
| Entity | Example | Confidence |
|--------|---------|-----------|
| MEDICAL_RECORD_NUMBER | MR-123456 | 0.85 |
| HEALTH_INSURANCE_ID | CCWH123456 | 0.80 |
| ICD10_CODE | A00.0 | 0.60 |

---

## Performance

### Processing Speed (Approximate)
- **Text files (.txt, .md):** <100ms per file
- **Word documents (.docx):** 100-300ms per file
- **Excel spreadsheets (.xlsx):** 200-500ms per file
- **PDFs (.pdf):** 300-1000ms per file (depending on page count)
- **Email messages (.eml, .msg):** 200-600ms per file

### Memory Usage
- Typically <500MB for batch of 100 files
- Scales linearly with file size and count

---

## Troubleshooting

### App Won't Start
```bash
# Make sure all dependencies are installed
pip install -r requirements.txt --upgrade

# Try running again
streamlit run streamlit_app.py
```

### High Memory Usage
- Process fewer files at once
- Clear results using "Clear All Results" button
- Restart the app

### Files Not Processing
- Verify file format is supported (.txt, .docx, .xlsx, .pdf, .eml, .msg)
- Check file size (very large files may timeout)
- Review error message in expanded file details

### Confidence Threshold Not Applying
- Threshold only affects **new processing**
- Reprocess files after adjusting threshold
- Existing results are not retroactively filtered

---

## Export & Integration

### JSON Export
Perfect for:
- Integration with other tools
- Detailed analysis/logging
- Backup and archival

Contains full entity information including position, confidence scores, and text.

### CSV Export
Perfect for:
- Spreadsheet analysis
- Reporting
- Quick summaries

Contains document-level statistics only.

---

## Tips & Best Practices

1. **Batch Processing:** Upload multiple files at once for efficiency
2. **Threshold Tuning:** Start at default 0.55, adjust based on your needs
3. **Export Regularly:** Download results before clearing history
4. **Review High-Confidence:** Focus on entities with >0.80 confidence first
5. **Use Analytics Tab:** Understand your data patterns before detailed review

---

## Security Notes

- ✅ **Local processing only** - no data sent to cloud
- ✅ **No permanent storage** - results cleared when you clear history
- ✅ **Session-based** - each Streamlit session is independent
- ⚠️ **Temporary storage** - files temporarily stored during processing, then deleted

---

## Example Workflows

### Workflow 1: Batch Investigation
1. Upload 50 documents
2. Process all at once
3. Go to Analytics tab to identify patterns
4. Export results as JSON
5. Download and review flagged documents

### Workflow 2: Threshold Testing
1. Upload test file
2. Process with default threshold (0.55)
3. Adjust confidence threshold in sidebar
4. Process again
5. Compare results to find optimal threshold

### Workflow 3: Regular Scanning
1. Upload weekly batch of documents
2. Process and review
3. Export summary as CSV
4. Archive results
5. Clear history for next batch

---

## Next Steps

- See [README.md](README.md) for technical details
- See [examples.py](examples.py) for programmatic usage
- See [GETTING_STARTED.md](GETTING_STARTED.md) for setup troubleshooting
