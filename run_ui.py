#!/usr/bin/env python3
"""
Launcher script for Streamlit UI
Runs: streamlit run streamlit_app.py
"""

import subprocess
import sys
import os

def main():
    print("🎨 Launching PII/PHI Detection UI...")
    print("-" * 50)
    print("Opening Streamlit app at http://localhost:8501")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "streamlit_app.py"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
    except KeyboardInterrupt:
        print("\n\n👋 Streamlit server stopped.")
        sys.exit(0)
    except FileNotFoundError:
        print("❌ Error: streamlit not found. Install with: pip install streamlit")
        sys.exit(1)

if __name__ == "__main__":
    main()
