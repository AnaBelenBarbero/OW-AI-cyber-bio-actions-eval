#!/bin/bash
# scripts/setup.sh - Setup script for OW-AI-cyber-bio-actions-eval

set -e  # Exit on error

echo "=== Setting up OW-AI-cyber-bio-actions-eval ==="

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT" || exit 1

# Optional: Install system dependencies
if [ "$1" == "--install-system-deps" ]; then
    echo "Installing system dependencies (requires sudo)..."
    sudo apt update
    sudo apt install -y libc6-dev libstdc++-11-dev
    sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 20
    sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-11 20
    sudo update-alternatives --set gcc /usr/bin/gcc-11
    sudo update-alternatives --set g++ /usr/bin/g++-11
    sudo apt-get update && sudo apt-get install -y python3.12-dev
    echo "System dependencies installed."
fi

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "UV not found. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for current session
    export PATH="$HOME/.cargo/bin:$PATH"
else
    echo "UV is already installed."
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with Python 3.12..."
    uv venv --python 3.12 --seed
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install vllm with torch-backend=auto
echo "Installing vllm with torch-backend=auto..."
uv pip install vllm --torch-backend=auto

# Install other dependencies
echo "Installing additional dependencies..."
uv pip install datasets peft bitsandbytes trl accelerate flashinfer-python streamlit \
    jupyterlab ipykernel ipywidgets

echo ""
echo "=== Setup complete! ==="
echo "To activate the environment, run:"
echo "  source .venv/bin/activate"