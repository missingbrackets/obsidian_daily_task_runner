#!/usr/bin/env bash
set -e

echo "=== Obsidian Daily Task Runner – Setup ==="

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "=== Setup complete! ==="
echo ""
echo "To run the app:"
echo "  source .venv/bin/activate"
echo "  streamlit run app.py"
echo ""
echo "Set your vault path via environment variable (optional):"
echo "  export OBSIDIAN_VAULT_PATH=/path/to/your/vault"
