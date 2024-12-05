# Share-Data Client Installation Guide
Welcome to the installation guide for the Share-Data Client on our MPC demo platform. This guide outlines three different installation methods, allowing you to choose based on your security concerns and bandwidth requirements.

## Installation Methods
### TL;DR
Available installation methods are A, B and C. In summary:

- Security: A > B > C
- Bandwidth requirement: A (<50MB) < C < B (>2GB)

### A. Install with Pre-Built Binaries

(Least Secure, Least Bandwidth)

This method relies on trusting pre-compiled binaries. It is the least secure but the simplest and fastest way to install the client.

- Bandwidth requirement: Low
- Downloads a shell script and two binaries (less than 50MB).

Note: The binaries are built directly from the source code using public GitHub workflows, defined and available in this repository. This ensures participants can verify the process and confirm binary integrity.

#### Procedure

```
curl -L -o share-data.sh https://github.com/ZKStats/mpc-demo-infra/releases/latest/download/share-data.sh
chmod +x share-data.sh
./share-data.sh <eth-address> <binance-api-key> <binance-api-secret>
```

To get the Binance API key and secret, follow the instructions in [Get Your Binance API Key](https://github.com/ZKStats/mpc-demo-infra/blob/main/mpc_demo_infra/client_cli/docker/README.md#step-1-get-your-binance-api-key)

### B. Install Using Docker

(Moderately Secure, High Bandwidth)

This method builds the client in an isolated environment using publicly available images, providing moderate security.

- Bandwidth requirement: Very High
- Downloads dependent Docker images (more than 6GB) and Docker itself if not already installed.

Note: The Dockerfile used for building the client is included in this repository, ensuring transparency.

#### Procedure
1. Install Docker Desktop or Docker Engine on your machine if not installed yet.
2. Follow the following steps:

    ```
    git clone https://github.com/ZKStats/mpc-demo-infra.git
    cd mpc-demo-infra/mpc_demo_infra/client_cli/docker
    ./build.sh
    ./share-data.sh <eth-address> <binance-api-key> <binance-api-secret>
    ```

To get the Binance API key and secret, follow the instructions in [Get Your Binance API Key](https://github.com/ZKStats/mpc-demo-infra/blob/main/mpc_demo_infra/client_cli/docker/README.md#step-1-get-your-binance-api-key)

### C. Build the Client Manually

(Most Secure, Moderate Bandwidth)

This method involves building the client entirely from the source code, offering the most security through full transparency and control.

- Bandwidth requirement: Moderate
- Downloads two repositories and dependencies for Rust and Python3. Additional downloads may include Rust, Python3, and Poetry if not already installed.

#### Procedure

1. Install Rust (if not installed)
```
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
```

2. Install Binance Prover
```
git clone https://github.com/ZKStats/tlsn.git
cd tlsn
git checkout mpspdz-compat
cd tlsn
cargo build --release --example binance_prover
```

3. Install Python3 and Poetry (if not installed)
- Ubuntu 24.04
```
apt-get update && apt-get install -y python3 python3-venv python3-pip curl pipx git automake build-essential clang cmake git libboost-dev libboost-iostreams-dev libboost-thread-dev libgmp-dev libntl-dev libsodium-dev libssl-dev libtool pkg-config libmpfr-dev libmpc-dev && apt-get clean && pipx install poetry && pipx ensurepath
```

- MacOS (Intel/Apple Silicon)

3.1 Install Homebrew (if not installed)
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" # only if brew is not installed
```

3.2 Install Python3 (if not installed)
```
brew install python
```

4. Install MPC demo infrastructure
```
git clone https://github.com/ZKStats/mpc-demo-infra.git
cd mpc-demo-infra
python3 -m venv venv
source venv/bin/activate
venv/bin/pip install -U pip setuptools
venv/bin/pip install poetry
poetry install
cp mpc_demo_infra/client_cli/.env.client_cli .
```

5. Initiate data sharing process
```
poetry run client-share-data <eth-address> <binance-api-key> <binance-api-secret>
```

To get the Binance API key and secret, follow the instructions in [Get Your Binance API Key](https://github.com/ZKStats/mpc-demo-infra/blob/main/mpc_demo_infra/client_cli/docker/README.md#step-1-get-your-binance-api-key)

## Troubleshooting and Support
If you encounter any issues during installation, feel free to open an issue in our [GitHub repository](https://github.com/ZKStats/mpc-demo-infra).

