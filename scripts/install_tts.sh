#!/bin/bash
set -e

echo "Installing Robotic Psalms TTS dependencies..."

# Install system TTS packages
sudo apt-get update
sudo apt-get install -y \
    espeak-ng \
    libespeak-ng-dev \
    espeak \
    libespeak-dev 


# Install Python dependencies
echo "Installing Python packages..."
pip install -e ".[espeak-ng]"

# Validate installation
echo "Validating installation..."
python -c "import espeak; print('TTS imports successful!')"