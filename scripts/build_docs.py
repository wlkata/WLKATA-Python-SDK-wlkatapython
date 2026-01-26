#!/usr/bin/env python3
"""
Script to build Sphinx documentation.

Usage:
    python scripts/build_docs.py
"""

import os
import sys
import subprocess
import locale
from pathlib import Path

def main():
    """Build the Sphinx documentation."""
    # Get the project root
    project_root = Path(__file__).parent.parent

    # Check if docs directory exists
    docs_dir = project_root / 'docs'
    if not docs_dir.exists():
        print("Error: docs directory not found!")
        sys.exit(1)

    # Check if sphinx-build is available
    try:
        import sphinx
    except ImportError:
        print("Error: sphinx not installed. Install with: uv pip install -e '.[docs]'")
        sys.exit(1)

    # Build directory
    build_dir = docs_dir / '_build' / 'html'
    build_dir.mkdir(parents=True, exist_ok=True)

    # Run sphinx-build
    cmd = [
        sys.executable, '-m', 'sphinx',
        '-b', 'html',  # builder
        '-W',  # treat warnings as errors
        '-E',  # rebuild all files
        str(docs_dir),  # source directory
        str(build_dir)  # output directory
    ]

    print(f"Building documentation from {docs_dir} to {build_dir}")

    # Set locale to avoid Sphinx locale errors
    os.environ['LC_ALL'] = 'C.UTF-8'
    os.environ['LANG'] = 'C.UTF-8'

    result = subprocess.run(cmd, cwd=project_root)

    if result.returncode == 0:
        print(f"Documentation built successfully! Open {build_dir / 'index.html'} in your browser.")
    else:
        print("Documentation build failed!")
        sys.exit(result.returncode)

if __name__ == '__main__':
    main()