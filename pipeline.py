"""
PII/PHI Detection and Extraction Pipeline
End-to-end orchestrator for analyzing documents from data breach investigations.

Stages:
  1. Extract raw text from every file
  2. Triage: flag documents containing PII/PHI
  3. Structured extraction: extract all PII/PHI as JSON (uses Presidio matches in POC)
  4. Reporting: generate results.json and summary_report.json for human reviewers

Usage:
    python pipeline.py /path/to/documents/directory [--output /path/to/output]
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Tuple

# Add extractors and detectors to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extractors.file_extractor import FileExtractor, ExtractionResult
from detectors.pii_phi_detector import PiiPhiDetector, TriageResult


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PiiPhiPipeline:
    """Main orchestrator for the PII/PHI detection pipeline."""

    def __init__(self, output_dir: str = "output"):
        """
        Initialize the pipeline.
        
        Args:
            output_dir: Directory to write results.json and summary_report.json
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.extractor = FileExtractor(log_level="INFO")
        self.detector = PiiPhiDetector(use_spacy_ner=False)

        # Tracking
        self.results = []
        self.flagged_documents = []
        self.clean_documents = []
        self.error_documents = []
        self.ocr_queue = []

        self.start_time = None
        self.end_time = None

    def process_directory(self, directory: str) -> None:
        """
        Main entry point: process all files in a directory recursively.
        
        Args:
            directory: Root directory to scan
        """
        directory = Path(directory)

        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            sys.exit(1)

        logger.info(f"Starting PII/PHI extraction pipeline on: {directory}")
        self.start_time = datetime.now()

        # Collect all supported files
        files_to_process = self._find_supported_files(directory)
        logger.info(f"Found {len(files_to_process)} supported files to process")

        # Process each file: Stage 1 (extract) → Stage 2 (triage)
        for file_index, filepath in enumerate(files_to_process, 1):
            logger.info(f"[{file_index}/{len(files_to_process)}] Processing: {filepath}")

            # Stage 1: Extract text
            extraction_result = self.extractor.extract(str(filepath))

            # Check extraction status
            if extraction_result.extraction_status == "needs_ocr":
                logger.info(f"  → OCR required; adding to queue")
                self.ocr_queue.append(extraction_result)
                self.results.append(extraction_result.to_dict())
                continue

            if extraction_result.extraction_status == "error":
                logger.warning(f"  → Extraction failed: {extraction_result.error}")
                self.error_documents.append(extraction_result)
                self.results.append(extraction_result.to_dict())
                continue

            if extraction_result.extraction_status == "empty":
                logger.info(f"  → File is empty; skipping triage")
                self.clean_documents.append(extraction_result)
                self.results.append(extraction_result.to_dict())
                continue

            # Stage 2: Triage (PII/PHI detection)
            triage_result = self.detector.triage(extraction_result.text)

            # Merge results
            final_result = self._merge_results(extraction_result, triage_result)

            if final_result["flagged_for_review"]:
                logger.info(f"  → FLAGGED: {final_result['match_count']} matches found")
                self.flagged_documents.append(final_result)
            else:
                logger.info(f"  → Clean (no PII/PHI detected)")
                self.clean_documents.append(final_result)

            self.results.append(final_result)

        self.end_time = datetime.now()

        # Generate reports
        self._write_results_json()
        self._write_summary_report()
        self._print_human_summary()

    def _find_supported_files(self, directory: Path) -> List[Path]:
        """Recursively find all supported file types."""
        supported_files = []
        for root, dirs, files in os.walk(directory):
            for filename in files:
                filepath = Path(root) / filename
                ext = filepath.suffix.lower()
                if ext in FileExtractor.SUPPORTED_EXTENSIONS:
                    supported_files.append(filepath)
        return sorted(supported_files)

    def _merge_results(
        self,
        extraction_result: ExtractionResult,
        triage_result: TriageResult
    ) -> Dict[str, Any]:
        """Merge extraction and triage results into a single document result."""
        result_dict = extraction_result.to_dict()

        # Add triage results
        result_dict["pii_phi_matches"] = triage_result.pii_phi_matches
        result_dict["match_count"] = triage_result.match_count
        result_dict["contains_pii"] = triage_result.contains_pii
        result_dict["contains_phi"] = triage_result.contains_phi
        result_dict["flagged_for_review"] = triage_result.flagged_for_review

        return result_dict

    def _write_results_json(self) -> None:
        """Write results.json with full per-document results."""
        output_file = self.output_dir / "results.json"

        logger.info(f"Writing full results to: {output_file}")

        # Prepare data for JSON (ensure serializable)
        json_results = []
        for result in self.results:
            json_result = self._make_json_serializable(result)
            json_results.append(json_result)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_results, f, indent=2, ensure_ascii=False)

        logger.info(f"Wrote {len(json_results)} documents to {output_file}")

    def _write_summary_report(self) -> None:
        """Write summary_report.json with aggregate statistics."""
        output_file = self.output_dir / "summary_report.json"

        logger.info(f"Writing summary report to: {output_file}")

        # Entity breakdown
        entity_breakdown = defaultdict(int)
        pii_count = 0
        phi_count = 0

        for result in self.results:
            for match in result.get("pii_phi_matches", []):
                entity_type = match.get("entity_type")
                entity_breakdown[entity_type] += 1

                if match.get("category") == "PII":
                    pii_count += 1
                elif match.get("category") == "PHI":
                    phi_count += 1

        # Filetype breakdown
        filetype_breakdown = defaultdict(lambda: {"total": 0, "flagged": 0})
        for result in self.results:
            filetype = result.get("filetype", "unknown")
            filetype_breakdown[filetype]["total"] += 1

            if result.get("flagged_for_review"):
                filetype_breakdown[filetype]["flagged"] += 1

        summary = {
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": (self.end_time - self.start_time).total_seconds(),
            "total_documents": len(self.results),
            "flagged_documents": len(self.flagged_documents),
            "clean_documents": len(self.clean_documents),
            "error_documents": len(self.error_documents),
            "needs_ocr": len(self.ocr_queue),
            "pii_document_count": sum(1 for r in self.results if r.get("contains_pii")),
            "phi_document_count": sum(1 for r in self.results if r.get("contains_phi")),
            "total_matches": sum(r.get("match_count", 0) for r in self.results),
            "pii_matches": pii_count,
            "phi_matches": phi_count,
            "entity_breakdown": dict(entity_breakdown),
            "by_filetype": dict(filetype_breakdown)
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"Wrote summary report to {output_file}")

    def _print_human_summary(self) -> None:
        """Print human-readable summary to stdout."""
        duration = (self.end_time - self.start_time).total_seconds()

        print("\n" + "="*70)
        print("PII/PHI EXTRACTION PIPELINE - SUMMARY REPORT")
        print("="*70)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Processing time: {duration:.2f} seconds")
        print()

        print(f"Total documents processed: {len(self.results)}")
        print(f"  ✓ Flagged for review: {len(self.flagged_documents)}")
        print(f"  ✓ Clean (no PII/PHI): {len(self.clean_documents)}")
        print(f"  ✗ Errors: {len(self.error_documents)}")
        print(f"  ⚠ Need OCR: {len(self.ocr_queue)}")
        print()

        # PII/PHI breakdown
        pii_docs = sum(1 for r in self.results if r.get("contains_pii"))
        phi_docs = sum(1 for r in self.results if r.get("contains_phi"))
        total_matches = sum(r.get("match_count", 0) for r in self.results)

        print(f"PII/PHI Detection Summary:")
        print(f"  Documents with PII: {pii_docs}")
        print(f"  Documents with PHI: {phi_docs}")
        print(f"  Total entities detected: {total_matches}")
        print()

        # Entity breakdown
        entity_breakdown = defaultdict(int)
        for result in self.results:
            for match in result.get("pii_phi_matches", []):
                entity_breakdown[match.get("entity_type")] += 1

        if entity_breakdown:
            print("Entity Breakdown:")
            for entity_type, count in sorted(entity_breakdown.items(), key=lambda x: x[1], reverse=True):
                label = self.detector.ENTITY_LABELS.get(entity_type, entity_type)
                print(f"  {label}: {count}")
            print()

        # Filetype breakdown
        filetype_breakdown = defaultdict(lambda: {"total": 0, "flagged": 0})
        for result in self.results:
            filetype = result.get("filetype", "unknown")
            filetype_breakdown[filetype]["total"] += 1
            if result.get("flagged_for_review"):
                filetype_breakdown[filetype]["flagged"] += 1

        if filetype_breakdown:
            print("Breakdown by File Type:")
            for filetype in sorted(filetype_breakdown.keys()):
                stats = filetype_breakdown[filetype]
                pct = (stats["flagged"] / stats["total"] * 100) if stats["total"] > 0 else 0
                print(f"  {filetype}: {stats['total']} total, {stats['flagged']} flagged ({pct:.1f}%)")
            print()

        # Output files
        print(f"Output files:")
        print(f"  • {self.output_dir / 'results.json'}")
        print(f"  • {self.output_dir / 'summary_report.json'}")
        print()

        # Next steps
        if self.ocr_queue:
            print(f"⚠ NOTE: {len(self.ocr_queue)} documents require OCR processing.")
            print(f"  Consider running these through PaddleOCR or Tesseract and re-entering the pipeline.")
            print()

        print("="*70)

    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert objects to JSON-serializable types."""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif hasattr(obj, 'isoformat'):  # datetime
            return obj.isoformat()
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            return str(obj)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PII/PHI Detection and Extraction Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline.py /path/to/documents
  python pipeline.py /data/breach_docs --output /results/output
        """
    )

    parser.add_argument(
        "directory",
        help="Root directory containing documents to analyze"
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Output directory for results (default: output)"
    )

    args = parser.parse_args()

    # Create and run pipeline
    pipeline = PiiPhiPipeline(output_dir=args.output)
    pipeline.process_directory(args.directory)


if __name__ == "__main__":
    main()
