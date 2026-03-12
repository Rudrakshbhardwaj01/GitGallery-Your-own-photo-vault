#!/usr/bin/env python3
"""Launch GitGallery desktop application."""

import sys
from pathlib import Path

# Ensure project root is on path
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Import config first
from gitgallery.app.config import LOGS_DIR, ensure_directories

# Create required directories
ensure_directories()

# Setup logging
from gitgallery.utils.logger import setup_logging
setup_logging(LOGS_DIR)

# Now import the main application
from gitgallery.app.main import main

if __name__ == "__main__":
    sys.exit(main())