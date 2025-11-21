"""Application entry point - wrapper script for easier execution."""

import sys
from pathlib import Path

# Add the current directory to Python path to ensure imports work correctly
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the main application
from call_summarizer.app import main

if __name__ == "__main__":
    main()

