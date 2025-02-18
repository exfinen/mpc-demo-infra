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
    [ "$1" = true ] && echo "*Installed*" || echo "-"
}

append_target() {
    if [ -z "$install_target" ]; then
        install_target="$1"
    else
        install_target="$install_target, $1"
    fi
}

print_usage() {
    echo "Usage: ./setup_env.sh [--setup-coord|--setup-party|--setup-client|--setup-consumer-api]"
    echo "Options:"
    echo "  --coord: Setup environment for Coordination Server"
    echo "  --party: Setup environment for Computation Party Server"
    echo "  --client: Setup environment for Client CLI"
    echo "  --consumer: Setup environment for Data Consumer API Server"
    echo "  --notary: Setup environment for Notary Server"
    echo "  --verbose: Show outputs from subprocesses"
    echo "  No option: Setup environment for all servers"
}

# Parse command line arguments
install_mpspdz=false
install_prover=false
install_verifier=false
install_notary=false
install_target=""

is_verbose=false

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --coord)
            install_verifier=true
            append_target "Coordination Server"
            ;;
        --party)
            install_mpspdz=true
            install_verifier=true
            append_target "Computation Party Server"
            ;;
        --client)
            install_prover=true
            install_rust=true
            append_target "Client CLI"
            ;;
        --consumer)
            append_target "Data Consumer API Server"
            ;;
        --notary)
            install_notary=true
            append_target "Notary Server"
            ;;
        --verbose)
            is_verbose=true
            ;;
        *)
            print_usage
            exit 1
            ;;
    esac
    shift
done

if [ "$is_verbose" = true ]; then
    set -x
    OUT_REDIR=""
else
    OUT_REDIR=">/dev/null 2>&1"
fi

all_servers="All servers"

if [ -z "$install_target" ]; then
    install_mpspdz=true
    install_prover=true
    install_verifier=true
    install_notary=true
    install_target=$all_servers
fi

if [ "$install_prover" = true ] || [ "$install_verifier" = true ] || [ "$install_notary" = true ]; then
    install_rust=true
else
    install_rust=false
fi

echo "Installation Target: $install_target"
echo "  - MP-SPDZ: $(inst_pp "$install_mpspdz")"
echo "  - Rust: $(inst_pp "$install_rust")"
echo "    - Binance Prover: $(inst_pp "$install_prover")"
echo "    - Binance Verifier: $(inst_pp "$install_verifier")"
echo "    - Notary Server: $(inst_pp "$install_notary")"
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
        eval "sudo apt install -y openssl $OUT_REDIR"
    else
        eval "brew install openssl $OUT_REDIR"
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
        eval "sudo apt install -y pkg-config $OUT_REDIR"
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
        eval "sudo apt install -y automake build-essential clang cmake git libboost-dev libboost-iostreams-dev libboost-thread-dev libgmp-dev libntl-dev libsodium-dev libssl-dev libtool python3 $OUT_REDIR"
        eval "sudo apt install -y libboost-all-dev $OUT_REDIR"
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

      # Generate self-signed certificate if all servers configuration
      if [ "$install_target" = "$all_servers" ]; then
        print "Generating self-signed cert..."
        spushd fixture/tls

        # openssl genpkey -algorithm RSA -out notary.key -pkeyopt rsa_keygen_bits:2048 \
        # && openssl req -new -key notary.key -out request.csr -subj "/C=US/ST=State/L=City/O=Organization/OU=Department/CN=127.0.0.1" \
        # && openssl x509 -req -in request.csr -signkey notary.key -out notary.crt -days 365 -extfile openssl.cnf -extensions v3_req

        # copy notary.crt to repository root so that binance prover can use
        cp notary.crt $MPC_DEMO_INFRA_ROOT
        spopd # pushd fixture/tls
      fi

      cp -R fixture ../target/release
      mkdir -p ../target/release/config
      cp $MPC_DEMO_INFRA_ROOT/mpc_demo_infra/notary_server/docker/config.yaml ../target/release/config
      spopd # pushd notary/server
    fi

    if [ "$install_prover" = true ] || [ "$install_verifier" = true ]; then
        spushd tlsn
        eval "cargo clean $OUT_REDIR"
        spopd # pushd tlsn
    fi

    # Install Binance Prover if so specified
    if [ "$install_prover" = true ]; then
        print "Building Binance Prover..."
        spushd tlsn
        eval "cargo build --release --example binance_prover $OUT_REDIR"

        spushd notary/target/release
        if ls binance_prover-* > /dev/null 2>&1; then
            mv -f binance_prover-* binance_prover
        fi
        spopd # pushd notary/target/release
        spopd # pushd tlsn
    fi

    # Install Binance Verifier if so specified
    if [ "$install_verifier" = true ]; then
        print "Building Binance Verifier..."
        spushd tlsn
        eval "cargo build --release --example binance_verifier $OUT_REDIR"
        spopd # pushd tlsn

        spushd notary/target/release
        if ls binance_verifier-* > /dev/null 2>&1; then
            mv -f binance_verifier-* release/binance_verifier
        fi
        spopd # pushd notary/target/release
        spopd # pushd tlsn
    fi

    spopd # pushd ../tlsn
fi

echo -e "\nEnvironment setup is complete."

