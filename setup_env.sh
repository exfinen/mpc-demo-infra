#!/bin/bash

MPC_PROTOCOL="malicious-rep-ring"
NUM_PARTIES=3

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

get_num_cores() {
    if [[ "$(detect_os)" == 'linux' ]]; then
        nproc
    elif [[ "$(detect_os)" == 'macos' ]]; then
        sysctl -n hw.ncpu
    else
        echo '1'
    fi
}

# Default value for MP-SPDZ setup
setup_mpspdz=false

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --setup-mpspdz) setup_mpspdz=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Update system
if [ "$(detect_os)" == "linux" ]; then
    sudo apt update
else
    brew update
fi

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
    if [ "$(detect_os)" == "linux" ]; then
        sudo apt install -y python3-poetry
    else
        curl -sSL https://install.python-poetry.org | python3 -
    fi
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


# Install pkg-config (used by TLSN)
if [ "$(detect_os)" == "linux" ]; then
    echo "Installing pkg-config..."
    sudo apt install -y pkg-config
fi

# Clone TLSN repository if not present
if [ ! -d "../tlsn" ]; then
    echo "Cloning TLSN repository..."
    cd ..
    git clone https://github.com/ZKStats/tlsn
    cd tlsn
    git checkout mpspdz-compat
    cd tlsn/examples
    cargo build --release --example simple_verifier
    cd ../../../mpc-demo-infra
else
    echo "TLSN repository already exists."
fi

# Setup MP-SPDZ if flag is set
if [ "$setup_mpspdz" = true ]; then
    echo "Setting up MP-SPDZ..."
    if [ ! -d "../MP-SPDZ" ]; then
        if [ "$(detect_os)" == "linux" ]; then
            sudo apt install -y automake build-essential clang cmake git libboost-dev libboost-iostreams-dev libboost-thread-dev libgmp-dev libntl-dev libsodium-dev libssl-dev libtool python3
            sudo apt install -y libboost-all-dev
        fi
        echo "Cloning MP-SPDZ repository..."
        cd ..
        git clone https://github.com/ZKStats/MP-SPDZ
        cd MP-SPDZ
        git checkout demo_client
        git submodule update --init --recursive

        # Add MOD to CONFIG.mine if not already present
        if ! grep -q "MOD = -DGFP_MOD_SZ=5 -DRING_SIZE=257" CONFIG.mine; then
            echo "MOD = -DGFP_MOD_SZ=5 -DRING_SIZE=257" >> CONFIG.mine
        fi

        # Install MP-SPDZ
        make setup

        # Build VM
        make -j$(get_num_cores) ${MPC_PROTOCOL}-party.x

        # Generate keys for all parties
        ./Scripts/setup-ssl.sh $NUM_PARTIES

        cd ../mpc-demo-infra
    else
        echo "MP-SPDZ repository already exists."
    fi
else
    echo "Skipping MP-SPDZ setup."
fi

# Set up Python virtual environment and install dependencies
# setting PYTHON_KEYRING_BACKEND to avoid potential keyring
# https://github.com/python-poetry/poetry/issues/1917#issuecomment-1235998997
PYTHON_KEYRING_BACKEND=keyring.backends.fail.Keyring  poetry install

echo "Environment setup complete. Please ensure you have the correct versions of all dependencies."
