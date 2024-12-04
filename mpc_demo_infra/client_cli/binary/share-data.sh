#!/bin/bash

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <eth-address> <binance-api-key> <binance-api-secret>"
    exit 1
fi

if [[ "$OSTYPE" == "darwin"* ]]; then
    if [[ "$(uname -m)" == "x86_64" ]]; then
        prover_suffix=macos_sonoma
        prover_url=https://github.com/ZKStats/tlsn/releases/download/binance_prover_20241202_054257/binance_prover_macos_sonoma

        share_data_suffix=macos_ventura
        share_data_url=https://github.com/ZKStats/mpc-demo-infra/releases/download/share_data_20241204_011506/share_data_macos_ventura

    elif [[ "$(uname -m)" == "arm64" ]]; then
        prover_suffix=macos_sonoma_arm64
        prover_url=https://github.com/ZKStats/tlsn/releases/download/binance_prover_20241202_054257/binance_prover_macos_sonoma_arm64

        share_data_suffix=macos_sonoma_arm64
        share_data_url=https://github.com/ZKStats/mpc-demo-infra/releases/download/share_data_20241204_011506/share_data_macos_sonoma_arm64

    else
        echo "Unsupported architecture: $OSTYPE"
        exit 1
    fi
    
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    for cmd in curl; do
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

    prover_suffix=ubuntu_noble
    prover_url=https://github.com/ZKStats/tlsn/releases/download/binance_prover_20241202_054257/binance_prover_ubuntu_noble

    share_data_suffix=ubuntu_noble
    share_data_url=https://github.com/ZKStats/mpc-demo-infra/releases/download/share_data_20241204_011506/share_data_ubuntu_noble

    if [[ "$version" != "24.04" ]]; then
        echo "Unsupported Ubuntu version: $ubuntu_version. Trying binary for Ubuntu 24.04."
    fi

    for cmd in curl; do
        if ! command -v $cmd &> /dev/null; then
            echo "Installing $cmd..."
            sudo apt-get install -y $cmd || {
                echo "Failed to install $cmd. Try running: sudo apt-get update";
                exit 1;
            }
        fi
    done
fi

if [ ! -f binance_prover ]; then
    binance_prover=binance_prover_$prover_suffix
    echo "Downloading $binance_prover..."
    curl -L -o binance_prover $prover_url
    chmod +x binance_prover
fi

if [ ! -f share_data ]; then
    share_data=share_data_$share_data_suffix
    echo "Downloading $share_data..."
    curl -L -o share_data $share_data_url
    chmod +x share_data
fi

echo "Started sharing data..."
./share_data $1 $2 $3

