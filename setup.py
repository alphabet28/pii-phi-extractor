#!/usr/bin/env python3
"""
Quick Installation Script
Run this to set up and test the PII/PHI pipeline in one go.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a shell command and report status."""
    print(f"\n{'='*70}")
    print(f"→ {description}")
    print(f"{'='*70}")
    try:
        result = subprocess.run(cmd, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed: {e}")
        return False


def main():
    print("\n" + "="*70)
    print("PII/PHI EXTRACTION PIPELINE - QUICK INSTALL")
    print("="*70)

    # Check Python version
    if sys.version_info < (3, 8):
        print(f"✗ Python {sys.version_info.major}.{sys.version_info.minor} (requires 3.8+)")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} OK")

    # Step 1: Install dependencies
    print("\n[Step 1/4] Installing dependencies from requirements.txt...")
    if not run_command(
        "pip install -r requirements.txt",
        "Installing pip packages"
    ):
        print("Try running manually: pip install -r requirements.txt")
        sys.exit(1)

    # Step 2: Verify setup
    print("\n[Step 2/4] Verifying setup...")
    if not run_command(
        "python verify_setup.py",
        "Running verification script"
    ):
        print("Verification failed. Check the output above.")
        sys.exit(1)

    # Step 3: Test with sample documents
    print("\n[Step 3/4] Testing with sample documents...")
    if not run_command(
        "python pipeline.py sample_docs/ --output output/",
        "Running pipeline on sample_docs/"
    ):
        print("Pipeline failed. Check the output above.")
        sys.exit(1)

    # Step 4: Show results
    print("\n[Step 4/4] Displaying results...")
    results_file = Path("output/summary_report.json")
    if results_file.exists():
        print("\n✓ Results written to output/")
        print(f"  • {results_file}")
        print(f"  • output/results.json")
        print("\nPreview of summary report:")
        try:
            import json
            with open(results_file) as f:
                summary = json.load(f)
            print(f"  Total documents: {summary['total_documents']}")
            print(f"  Flagged for review: {summary['flagged_documents']}")
            print(f"  Total entities detected: {summary['total_matches']}")
        except:
            pass
    else:
        print("✗ Results file not found")
        sys.exit(1)

    # Success!
    print("\n" + "="*70)
    print("✓ INSTALLATION COMPLETE!")
    print("="*70)
    print("\nYou can now process your documents with:")
    print("  python pipeline.py /path/to/your/documents\n")
    print("For more information, see:")
    print("  • QUICKSTART.md - Quick start guide")
    print("  • README.md - Full documentation")
    print("  • PROJECT_STRUCTURE.md - Architecture details")
    print("  • examples.py - Advanced usage examples")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
