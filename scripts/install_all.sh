#!/bin/bash
set -e

echo "Installing Robotic Psalms dependencies..."

# System packages
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    python3-venv \
    portaudio19-dev \
    libasound2-dev \
    espeak-ng \
    libespeak-ng-dev \
    espeak \
    libespeak-dev 

# Create and activate virtual environment
echo "Setting up Python environment..."
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install project with all extras
echo "Installing Python packages..."
pip install -e ".[all]"

# Validate installation
echo "Validating installation..."
python -c "import robotic_psalms; print('Installation successful!')"

echo "Done! Activate the environment with: source .venv/bin/activate"