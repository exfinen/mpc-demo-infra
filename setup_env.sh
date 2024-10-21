#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Update system
sudo apt update

# Install Python 3 if not present
if ! command_exists python3; then
    echo "Installing Python 3..."
    sudo apt install -y python3 python3-venv python3-pip
else
    echo "Python 3 is already installed."
fi

# Install Poetry if not present
if ! command_exists poetry; then
    echo "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
else
    echo "Poetry is already installed."
fi

# Install Rust and Cargo if not present
if ! command_exists cargo; then
    echo "Installing Rust and Cargo..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source $HOME/.cargo/env
else
    echo "Rust and Cargo are already installed."
fi

# Clone TLSN repository if not present
if [ ! -d "../tlsn" ]; then
    echo "Cloning TLSN repository..."
    cd ..
    git clone https://github.com/ZKStats/tlsn
    cd tlsn
    git checkout mpspdz-compat
    cd ../mpc-demo-infra
else
    echo "TLSN repository already exists."
fi

# Clone MP-SPDZ repository if not present
if [ ! -d "../MP-SPDZ" ]; then
    echo "Cloning MP-SPDZ repository..."
    cd ..
    git clone https://github.com/ZKStats/MP-SPDZ
    cd MP-SPDZ
    git checkout demo_client

    # Add MOD to CONFIG.mine if not already present
    if ! grep -q "MOD = -DGFP_MOD_SZ=5" CONFIG.mine; then
        echo "MOD = -DGFP_MOD_SZ=5" >> CONFIG.mine
    fi

    # Install MP-SPDZ
    make setup

    # Build VM
    make semi-party.x

    cd ../mpc-demo-infra
else
    echo "MP-SPDZ repository already exists."
fi

# Set up Python virtual environment and install dependencies
poetry env use python3
poetry install

echo "Environment setup complete. Please ensure you have the correct versions of all dependencies."
