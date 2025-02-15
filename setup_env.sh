#!/bin/bash

set -e 

MPC_PROTOCOL="malicious-rep-ring"
NUM_PARTIES=3

is_debug=false

if [ "$is_debug" = true ]; then
    set -x
    OUT_REDIR=""
else
    OUT_REDIR=">/dev/null 2>&1"
fi

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

print() {
    echo -e "===> $1"
}

spushd() {
    eval "pushd $1 $OUT_REDIR"
}

spopd() {
    eval "popd >/dev/null $OUT_REDIR"
}

inst_pp() {
    [ "$1" = true ] && echo "Installed" || echo "Not Installed"
}

# Parse command line arguments
if [ "$#" -gt 1 ]; then
    echo "Usage: ./setup_env.sh [--setup-coord|--setup-party|--setup-client|--setup-consumer-api]"
    echo "Options:"
    echo "  --coord: Setup environment for Coordination Server"
    echo "  --party: Setup environment for Computation Party Server"
    echo "  --client: Setup environment for Client CLI"
    echo "  --consumer: Setup environment for Data Consumer API Server"
    echo "  --notary: Setup environment for Notary Server"
    echo "  No argument: Setup environment for all servers"
    exit 1
fi

install_mpspdz=true
install_prover=true
install_verifier=true
install_notary=true
install_target="All servers"

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --coord)
            install_mpspdz=false
            install_prover=false
            install_verifier=true
            install_notary=false
            install_target="Coordination Server"
            ;;
        --party)
            install_mpspdz=true
            install_prover=false
            install_verifier=true
            install_notary=false
            install_target="Computation Party Server"
            ;;
        --client)
            install_mpspdz=false
            install_prover=true
            install_verifier=false
            install_rust=true
            install_notary=false
            install_target="Client CLI"
            ;;
        --consumer)
            install_mpspdz=false
            install_prover=false
            install_verifier=false
            install_notary=false
            install_target="Data Consumer API Server"
            ;;
        --notary)
            install_mpspdz=false
            install_prover=false
            install_verifier=false
            install_notary=true
            install_target="Notary Server"
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
    shift
done

if [ "$install_prover" = true ] || [ "$install_verifier" = true ] || [ "$install_notary" = true ]; then
    install_rust=true
else
    install_rust=false
fi

echo "Installation target: $install_target"
echo "  - MP-SPDZ: $(inst_pp "$install_mpspdz")"
echo "  - Rust: $(inst_pp "$install_rust")"
echo "    - Binance Prover: $(inst_pp "$install_prover")"
echo "    - Binance Verifier: $(inst_pp "$install_verifier")"
echo "    - notary server: $(inst_pp "$install_notary")"
echo ""

# Update package manager
print "Updating package manager..."
if [ "$(detect_os)" == "linux" ]; then
    eval "sudo apt update $OUT_REDIR"
else
    eval "brew update $OUT_REDIR"
fi

# Install Python 3 if not present
if ! command_exists python3; then
    print "Installing python3..."
    if [ "$(detect_os)" == "linux" ]; then
        eval "sudo apt install -y python3 python3-venv python3-pip $OUT_REDIR"
    else
        eval "brew install python3 $OUT_REDIR"
    fi 
fi

# Install poetry if not present
if ! command_exists poetry; then
    print "Installing poetry..."
    if [ ! -e venv ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    venv/bin/pip install -U pip setuptools
    venv/bin/pip install poetry
fi

# Install Python dependencies
if [ "$(detect_os)" == "linux" ]; then
    # setting PYTHON_KEYRING_BACKEND to avoid potential keyring
    # https://github.com/python-poetry/poetry/issues/1917#issuecomment-1235998997
    PYTHON_KEYRING_BACKEND=keyring.backends.fail.Keyring poetry install
else
    eval "poetry install $OUT_REDIR"
fi

# Install openssl if not present
if ! command_exists openssl; then
    print "Installing openssl..."
    if [ "$(detect_os)" == "linux" ]; then
        sudo apt install -y openssl
    else
        brew install openssl
    fi
fi

# Install Rust if so specified
if [ "$install_rust" = true ]; then
    # Update or newly install Rust
    if ! command_exists cargo; then
        print "Installing Rust and Cargo..."
        eval "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y $OUT_REDIR"
        source $HOME/.cargo/env
    else
        eval "rustup update $OUT_REDIR"
    fi

    # Install pkg-config (used by TLSN)
    if [ "$(detect_os)" == "linux" ]; then
        print "Installing pkg-config..."
        sudo apt install -y pkg-config
    fi
fi

# Create tlsn symbolic link if required and not present
if [ "$install_rust" = true ]; then
    if [ ! -L "../tlsn" ]; then
        if [ -e "../tlsn" ]; then
            echo "Unable to create a symbolic link ../tlsn because ../tlsn directory or file already exists"
            exit 1
        fi
        print "Creating symbolic link: ../tlsn -> ./tlsn"
        ln -s $(pwd)/tlsn ..
    fi
fi

# Create MP-SPDZ symbolic link if required and not present
if [ "$install_mpspdz" = true ]; then
    if [ ! -L "../MP-SPDZ" ]; then
        if [ -e "../MP-SPDZ" ]; then
            echo "Unable to create a symbolic link ../MP-SPDZ because ../MP-SPDZ directory or file already exists"
            exit 1
        fi
        print "Creating symbolic link: ../MP-SPDZ -> ./MP-SPDZ"
        ln -s $(pwd)/MP-SPDZ ..
    fi
fi

# Setup MP-SPDZ if so specified
if [ "$install_mpspdz" = true ]; then
    # Install dependencies
    # MP-SPDZ Makefile takes care of installing dependencis for macOS
    if [ "$(detect_os)" == "linux" ]; then
        sudo apt install -y automake build-essential clang cmake git libboost-dev libboost-iostreams-dev libboost-thread-dev libgmp-dev libntl-dev libsodium-dev libssl-dev libtool python3
        sudo apt install -y libboost-all-dev
    fi

    # Setup MP-SPDZ
    spushd ../MP-SPDZ
    git submodule update --init --recursive

    # Add CONFIG.mine with MOD if not already present
    touch CONFIG.mine
    if ! grep -q "MOD = -DGFP_MOD_SZ=5 -DRING_SIZE=257" CONFIG.mine; then
        echo "MOD = -DGFP_MOD_SZ=5 -DRING_SIZE=257" >> CONFIG.mine
    fi

    # Build MP-SPDZ and VM
    print "Building MP-SPDZ (setup)..."
    eval "make setup $OUT_REDIR"
    print "Building MP-SPDZ (vm)..."
    eval "make -j$(get_num_cores) ${MPC_PROTOCOL}-party.x $OUT_REDIR"

    # Generate keys for all parties
    print "Setting up SSL..."
    eval "./Scripts/setup-ssl.sh $NUM_PARTIES $OUT_REDIR"
    spopd # spushd ../MP-SPDZ
fi

if [ "$install_rust" = true ]; then
    MPC_DEMO_INFRA_ROOT=$(pwd)
    spushd ../tlsn

    # Install Notary Server if so specified
    if [ "$install_notary" = true ]; then
      print "Building Notary Server..."
      spushd notary/server
      eval "cargo build --release $OUT_REDIR"
      cp -R fixture ../target/release
      mkdir -p ../target/release/config
      cp $MPC_DEMO_INFRA_ROOT/mpc_demo_infra/notary_server/docker/config.yaml ../target/release/config
      spopd # pushd notary/server
    fi

    # Install Binance Prover if so specified
    if [ "$install_prover" = true ]; then
        print "Building Binance Prover..."
        spushd tlsn
        eval "cargo build --release --example binance_prover $OUT_REDIR"
        spopd # pushd tlsn
    fi

    # Install Binance Verifier if so specified
    if [ "$install_verifier" = true ]; then
        print "Building Binance Verifier..."
        spushd tlsn
        eval "cargo build --release --example binance_verifier $OUT_REDIR"
        spopd # pushd tlsn
    fi

    spopd # pushd ../tlsn
fi

echo -e "\nEnvironment setup is complete."

