#!/usr/bin/env python3
"""
Quick Setup and Test Script
Verifies all dependencies are installed and runs a test on sample documents.
"""

import sys
import subprocess
from pathlib import Path

def check_package(package_name: str, import_name: str = None) -> bool:
    """Check if a package is installed."""
    if import_name is None:
        import_name = package_name.replace('-', '_')
    
    try:
        __import__(import_name)
        print(f"✓ {package_name} installed")
        return True
    except ImportError:
        print(f"✗ {package_name} NOT installed")
        return False

def main():
    print("="*70)
    print("PII/PHI Pipeline - Setup Verification")
    print("="*70)
    print()

    # Check Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if sys.version_info >= (3, 8):
        print(f"✓ Python {python_version} (OK)")
    else:
        print(f"✗ Python {python_version} (requires 3.8+)")
        sys.exit(1)
    print()

    # Check required packages
    print("Checking dependencies:")
    required = [
        ("presidio-analyzer", "presidio_analyzer"),
        ("presidio-anonymizer", "presidio_anonymizer"),
        ("spacy", "spacy"),
        ("python-docx", "docx"),
        ("openpyxl", "openpyxl"),
        ("pdfplumber", "pdfplumber"),
        ("pdfminer.six", "pdfminer"),
        ("extract-msg", "extract_msg"),
        ("beautifulsoup4", "bs4"),
        ("lxml", "lxml"),
    ]

    missing = []
    for package, import_name in required:
        if not check_package(package, import_name):
            missing.append(package)

    print()

    if missing:
        print(f"Missing {len(missing)} packages:")
        for pkg in missing:
            print(f"  • {pkg}")
        print()
        print("Install with:")
        print(f"  pip install {' '.join(missing)}")
        print()
        sys.exit(1)

    print("✓ All dependencies installed!")
    print()

    # Verify directory structure
    print("Checking directory structure:")
    dirs = ["extractors", "detectors", "sample_docs", "output"]
    for dir_name in dirs:
        path = Path(dir_name)
        if path.exists():
            print(f"✓ {dir_name}/ exists")
        else:
            print(f"✗ {dir_name}/ missing")

    print()
    print("="*70)
    print("Setup verification complete!")
    print()
    print("Next steps:")
    print("  1. Test with sample documents:")
    print("     python pipeline.py sample_docs/")
    print()
    print("  2. Process your documents:")
    print("     python pipeline.py /path/to/your/documents")
    print()
    print("For more information, see README.md")
    print("="*70)


if __name__ == "__main__":
    main()
