#!/bin/bash
# Call Summarizer Launcher
# Double-click this file to launch the app

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ ! -f "venv/bin/activate" ]; then
    echo "Error: Virtual environment not found!"
    echo "Please ensure you're in the project directory and venv is set up."
    read -p "Press Enter to exit..."
    exit 1
fi

# Activate venv
source venv/bin/activate

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "Error: Python not found in virtual environment!"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo "Error: app.py not found!"
    read -p "Press Enter to exit..."
    exit 1
fi

# Set up environment
export VIRTUAL_ENV="$SCRIPT_DIR/venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"

# Run the application
echo "Starting Call Summarizer..."
echo "================================"
python app.py

# Keep terminal open if there's an error
if [ $? -ne 0 ]; then
    echo ""
    echo "================================"
    echo "Application exited with an error."
    read -p "Press Enter to close..."
fi

