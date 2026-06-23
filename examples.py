"""
Advanced Configuration Examples
Demonstrates how to customize the PII/PHI detection pipeline.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extractors.file_extractor import FileExtractor
from detectors.pii_phi_detector import PiiPhiDetector
import json


def example_1_custom_confidence_threshold():
    """Example 1: Use a custom confidence threshold for triage."""
    print("="*70)
    print("Example 1: Custom Confidence Threshold")
    print("="*70)
    
    # Create detector with default threshold (0.55)
    detector = PiiPhiDetector()
    
    test_text = """
    Social Security Number: 123-45-6789
    Email: john.doe@company.com
    """
    
    result = detector.triage(test_text)
    print(f"Matches with default threshold (0.55): {result.match_count}")
    
    # To use a different threshold, modify the detector's threshold:
    detector.CONFIDENCE_THRESHOLD = 0.70  # Higher = fewer detections
    result = detector.triage(test_text)
    print(f"Matches with threshold 0.70: {result.match_count}")
    
    detector.CONFIDENCE_THRESHOLD = 0.40  # Lower = more detections
    result = detector.triage(test_text)
    print(f"Matches with threshold 0.40: {result.match_count}")
    print()


def example_2_extract_and_triage_single_file():
    """Example 2: Extract and triage a single file programmatically."""
    print("="*70)
    print("Example 2: Extract and Triage Single File")
    print("="*70)
    
    # Extract text
    extractor = FileExtractor()
    extraction_result = extractor.extract("sample_docs/patient_record_1.txt")
    
    print(f"File: {extraction_result.filename}")
    print(f"Status: {extraction_result.extraction_status}")
    print(f"Text length: {len(extraction_result.text)} chars")
    print()
    
    # Triage
    if extraction_result.extraction_status == "success":
        detector = PiiPhiDetector()
        triage_result = detector.triage(extraction_result.text)
        
        print(f"PII/PHI Matches: {triage_result.match_count}")
        print(f"Contains PII: {triage_result.contains_pii}")
        print(f"Contains PHI: {triage_result.contains_phi}")
        print()
        
        # Show matches
        for match in triage_result.pii_phi_matches:
            print(f"  • {match['label']}: {match['value']} (confidence: {match['confidence']})")
    print()


def example_3_structured_extraction():
    """Example 3: Get structured output grouped by entity type."""
    print("="*70)
    print("Example 3: Structured Extraction (Grouped by Type)")
    print("="*70)
    
    extractor = FileExtractor()
    detector = PiiPhiDetector()
    
    extraction_result = extractor.extract("sample_docs/patient_record_1.txt")
    
    if extraction_result.extraction_status == "success":
        structured = detector.extract_structured(extraction_result.text)
        
        print(json.dumps(structured, indent=2))
    print()


def example_4_batch_processing_with_filtering():
    """Example 4: Process multiple files with filtering."""
    print("="*70)
    print("Example 4: Batch Processing with Filtering")
    print("="*70)
    
    from pathlib import Path
    
    extractor = FileExtractor()
    detector = PiiPhiDetector()
    
    sample_dir = Path("sample_docs")
    
    # Process all text files
    pii_documents = []
    phi_documents = []
    
    for filepath in sample_dir.glob("*.txt"):
        extraction_result = extractor.extract(str(filepath))
        
        if extraction_result.extraction_status != "success":
            continue
        
        triage_result = detector.triage(extraction_result.text)
        
        if triage_result.contains_pii:
            pii_documents.append({
                "filename": filepath.name,
                "matches": triage_result.match_count
            })
        
        if triage_result.contains_phi:
            phi_documents.append({
                "filename": filepath.name,
                "matches": triage_result.match_count
            })
    
    print(f"Documents with PII: {len(pii_documents)}")
    for doc in pii_documents:
        print(f"  • {doc['filename']}: {doc['matches']} matches")
    print()
    
    print(f"Documents with PHI: {len(phi_documents)}")
    for doc in phi_documents:
        print(f"  • {doc['filename']}: {doc['matches']} matches")
    print()


def example_5_custom_entity_mapping():
    """Example 5: Map entities to custom categories."""
    print("="*70)
    print("Example 5: Custom Entity Mapping")
    print("="*70)
    
    extractor = FileExtractor()
    detector = PiiPhiDetector()
    
    extraction_result = extractor.extract("sample_docs/employee_data.txt")
    
    if extraction_result.extraction_status == "success":
        triage_result = detector.triage(extraction_result.text)
        
        # Custom categorization
        financial = ["CREDIT_CARD", "US_BANK_NUMBER"]
        identity = ["US_SSN", "PASSPORT_NUMBER"]
        contact = ["EMAIL_ADDRESS", "PHONE_NUMBER"]
        medical = ["MEDICAL_RECORD_NUMBER", "HEALTH_INSURANCE_ID", "ICD10_CODE"]
        
        categories = {
            "Financial": [],
            "Identity": [],
            "Contact": [],
            "Medical": [],
            "Other": []
        }
        
        for match in triage_result.pii_phi_matches:
            entity_type = match["entity_type"]
            if entity_type in financial:
                categories["Financial"].append(match)
            elif entity_type in identity:
                categories["Identity"].append(match)
            elif entity_type in contact:
                categories["Contact"].append(match)
            elif entity_type in medical:
                categories["Medical"].append(match)
            else:
                categories["Other"].append(match)
        
        for category, matches in categories.items():
            if matches:
                print(f"{category}: {len(matches)} matches")
                for match in matches:
                    print(f"  • {match['label']}: {match['value']}")
    print()


def example_6_handling_different_file_formats():
    """Example 6: Handle different file formats."""
    print("="*70)
    print("Example 6: File Format Handling")
    print("="*70)
    
    from pathlib import Path
    
    extractor = FileExtractor()
    
    test_files = [
        "sample_docs/patient_record_1.txt",
        "sample_docs/employee_data.txt",
        "sample_docs/clean_document.txt"
    ]
    
    for filepath in test_files:
        if Path(filepath).exists():
            result = extractor.extract(filepath)
            
            print(f"File: {result.filename}")
            print(f"  Type: {result.filetype}")
            print(f"  Status: {result.extraction_status}")
            print(f"  Size: {len(result.text)} chars")
            
            if result.metadata:
                print(f"  Metadata: {result.metadata}")
            
            if result.error:
                print(f"  Error: {result.error}")
            
            print()


def example_7_performance_timing():
    """Example 7: Measure processing performance."""
    print("="*70)
    print("Example 7: Performance Timing")
    print("="*70)
    
    import time
    from pathlib import Path
    
    extractor = FileExtractor()
    detector = PiiPhiDetector()
    
    sample_dir = Path("sample_docs")
    files = list(sample_dir.glob("*.txt"))
    
    # Time extraction
    start = time.time()
    for filepath in files:
        extractor.extract(str(filepath))
    extraction_time = time.time() - start
    print(f"Extraction: {len(files)} files in {extraction_time:.3f}s")
    print(f"  → {len(files)/extraction_time:.1f} files/second")
    print()
    
    # Time triage
    start = time.time()
    for filepath in files:
        result = extractor.extract(str(filepath))
        if result.extraction_status == "success":
            detector.triage(result.text)
    triage_time = time.time() - start
    print(f"Triage: {len(files)} files in {triage_time:.3f}s")
    print(f"  → {len(files)/triage_time:.1f} files/second")
    print()


if __name__ == "__main__":
    # Run examples
    example_1_custom_confidence_threshold()
    example_2_extract_and_triage_single_file()
    example_3_structured_extraction()
    example_4_batch_processing_with_filtering()
    example_5_custom_entity_mapping()
    example_6_handling_different_file_formats()
    example_7_performance_timing()
    
    print("="*70)
    print("Examples complete! Modify these examples to customize the pipeline.")
    print("="*70)
