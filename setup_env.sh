#!/bin/bash

set -e 

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

# Parse command line arguments
setu_local=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --setup-local) setup_local=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

if [ "$setup_local" = true ]; then
    echo  "Setting up the environment for local deployment..."
else
    echo  "Setting up the environment for remote deployment..."
fi

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
fi

# Install Poetry if not present
if ! command_exists poetry; then
   if [ ! -e venv ]; then
       python3 -m venv venv
   fi
   source venv/bin/activate
   venv/bin/pip install -U pip setuptools
   venv/bin/pip install poetry
fi

# Update or newly install Rust
if ! command_exists cargo; then
    echo "Installing Rust and Cargo..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source $HOME/.cargo/env
else
    rustup update
fi

# Install pkg-config (used by TLSN)
if [ "$(detect_os)" == "linux" ]; then
    echo "Installing pkg-config..."
    sudo apt install -y pkg-config
fi

# Install Python dependencies
if [ "$(detect_os)" == "linux" ]; then
    # setting PYTHON_KEYRING_BACKEND to avoid potential keyring
    # https://github.com/python-poetry/poetry/issues/1917#issuecomment-1235998997
    PYTHON_KEYRING_BACKEND=keyring.backends.fail.Keyring poetry install
else
    $HOME/.local/bin/poetry install
fi

# Create tlsn symbolic link if missing
if [ ! -L "../tlsn" ]; then
    echo "Creating symbolic link: ../tlsn -> ./tlsn"
    ln -s $(pwd)/tlsn ..
fi

# Create MP-SPDZ symbolic link if missing
if [ ! -L "../MP-SPDZ" ]; then
    echo "Creating symbolic link: ../MP-SPDZ -> ./MP-SPDZ"
    ln -s $(pwd)/MP-SPDZ ..
fi

# Setup MP-SPDZ and tlsn if local flag is set
if [ "$setup_local" = true ]; then
    # Install dependencies
    if [ "$(detect_os)" == "linux" ]; then
        sudo apt install -y automake build-essential clang cmake git libboost-dev libboost-iostreams-dev libboost-thread-dev libgmp-dev libntl-dev libsodium-dev libssl-dev libtool python3
        sudo apt install -y libboost-all-dev
    else
        brew list boost &>/dev/null && brew upgrade boost || brew install boost
    fi

    # Setup MP-SPDZ
    echo "Setting up MP-SPDZ..."
    pushd ../MP-SPDZ
    git submodule update --init --recursive

    # Add CONFIG.mine with MOD if not already present
    touch CONFIG.mine
    if ! grep -q "MOD = -DGFP_MOD_SZ=5 -DRING_SIZE=257" CONFIG.mine; then
        echo "MOD = -DGFP_MOD_SZ=5 -DRING_SIZE=257" >> CONFIG.mine
    fi

    # Build MP-SPDZ and VM
    make setup
    make -j$(get_num_cores) ${MPC_PROTOCOL}-party.x

    # Generate keys for all parties
    ./Scripts/setup-ssl.sh $NUM_PARTIES
    popd

    # Setup tlsn
    echo "Setting up tlsn..."
    pushd ../tlsn

    # Build tlsn
    pushd notary/server
    cargo build --release
    cp -R fixture ../target/release
    popd

    # Build binance_prover/verifier
    pushd tlsn
    cargo build --release --example binance_prover
    cargo build --release --example binance_verifier
    popd

    popd
fi

echo "Environment setup complete. Please ensure you have the correct versions of all dependencies."

