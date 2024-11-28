#!/bin/bash

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <eth-address> <binance-api-key> <binance-api-secret>"
    exit 1
fi

if [[ "$OSTYPE" == "darwin"* ]]; then
    if [[ "$(uname -m)" == "x86_64" ]]; then
        export binary_suffix=macos_sonoma
    elif [[ "$(uname -m)" == "arm64" ]]; then
        export binary_suffix=macos_sonoma_arm64
    else
        echo "Unsupported architecture: $OSTYPE"
        exit 1
    fi
    
    # install jq if not available
    if ! command -v jq &> /dev/null; then
        # Check if Homebrew is installed
        if ! command -v brew &> /dev/null; then
            echo "Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        echo "Installing jq..."
        brew install jq
    fi

elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if command -v lsb_release &> /dev/null; then
        version=$(lsb_release -rs)
    elif [[ -f /etc/os-release ]]; then
        version=$(grep "^VERSION_ID=" /etc/os-release | cut -d'"' -f2)
    else
        echo "Failed to determine Ubuntu version."
        exit 1
    fi

    if [[ "$version" == "24.04" ]]; then
        export binary_suffix=ubuntu_noble
    else
        echo "Unsupported Ubuntu version: $ubuntu_version"
        exit 1
    fi

    # install jq if not available
    if ! command -v jq &> /dev/null; then
        echo "Installing jq..."
        sudo apt-get install -y jq
    fi
fi

binary_url=$(curl -sL \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $github_access_token" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/exfinen/tlsn/actions/artifacts \
  | jq -r '.artifacts[] | select(.name == ("binance_prover_" + env.binary_suffix)) | .archive_download_url')

echo "Downloading binance_prover from $binary_url..."
curl -sL \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $github_access_token" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -o binance_prover.zip \
  $binary_url

unzip binance_prover.zip
rm -f binance_prover.zip

binary_dir=../../../../tlsn/tlsn/target/examples
mv binance_prover_* $binary_dir/binance_prover
echo "copied binance_prover to $binary_dir"

