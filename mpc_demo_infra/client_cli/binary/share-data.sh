#!/bin/bash

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <eth-address> <binance-api-key> <binance-api-secret>"
    exit 1
fi

if [[ "$OSTYPE" == "darwin"* ]]; then
    if [[ "$(uname -m)" == "x86_64" ]]; then
        export binary_suffix=macos_sonoma
        export binary_url=https://github.com/ZKStats/tlsn/releases/download/binance_prover_20241130/binance_prover_macos_sonoma
    elif [[ "$(uname -m)" == "arm64" ]]; then
        export binary_suffix=macos_sonoma_arm64
        export binary_url=https://github.com/ZKStats/tlsn/releases/download/binance_prover_20241130/binance_prover_macos_sonoma_arm64
    else
        echo "Unsupported architecture: $OSTYPE"
        exit 1
    fi
    
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    for cmd in curl python3; do
        if ! command -v $cmd &> /dev/null; then
            echo "Installing $cmd..."
            brew install $cmd
        fi
    done

elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if command -v lsb_release &> /dev/null; then
        version=$(lsb_release -rs)
    elif [[ -f /etc/os-release ]]; then
        version=$(grep "^VERSION_ID=" /etc/os-release | cut -d'"' -f2)
    else
        echo "Failed to determine Ubuntu version."
        exit 1
    fi

    export binary_suffix=ubuntu_noble
    export binary_url=https://github.com/ZKStats/tlsn/releases/download/binance_prover_20241130/binance_prover_ubuntu_noble

    if [[ "$version" != "24.04" ]]; then
        echo "Unsupported Ubuntu version: $ubuntu_version. Trying binary for Ubuntu 24.04."
    fi

    for cmd in curl python3; do
        if ! command -v $cmd &> /dev/null; then
            echo "Installing $cmd..."
            sudo apt-get install -y $cmd || {
                echo "Failed to install $cmd. Try running: sudo apt-get update";
                exit 1;
            }
        fi
    done
fi

repository_root=../../..

echo "Downloading binance_prover for $binary_suffix..."
curl -L -o $repository_root/binance_prover $binary_url
chmod +x $repository_root/binance_prover

if ! command -v poetry &> /dev/null; then
    echo 'Install poetry...'
    VENV_PATH=./mpc-demo-venv
    mkdir -p $VENV_PATH

    python3 -m venv $VENV_PATH
    source $VENV_PATH/bin/activate

    $VENV_PATH/bin/pip install -U pip setuptools
    $VENV_PATH/bin/pip install poetry
fi

cd $repository_root
poetry install
poetry run client-share-data $1 $2 $3

