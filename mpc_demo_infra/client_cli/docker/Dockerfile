FROM ubuntu:24.04

SHELL ["/bin/bash", "-c"]
ENV PATH="/root/.cargo/bin:/root/.local/bin:${PATH}"

WORKDIR /root

RUN apt-get update && apt-get install -y python3 python3-venv python3-pip curl pipx git automake build-essential clang cmake git libboost-dev libboost-iostreams-dev libboost-thread-dev libgmp-dev libntl-dev libsodium-dev libssl-dev libtool pkg-config libmpfr-dev libmpc-dev libboost-filesystem-dev \
    && apt-get clean \
    && pipx install poetry \
    && pipx ensurepath

# Install mpc-demo-infra
RUN git clone https://github.com/ZKStats/mpc-demo-infra.git \
    && cd mpc-demo-infra \
    && PYTHON_KEYRING_BACKEND=keyring.backends.fail.Keyring poetry install

# Install rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Install simple_prover command
RUN git clone https://github.com/ZKStats/tlsn.git \
    && cd tlsn \
    && git checkout mpspdz-compat \
    && cd tlsn \
    && cargo build --release --example binance_prover

COPY .env.client_cli /root/mpc-demo-infra/

WORKDIR /root/mpc-demo-infra

ENTRYPOINT ["poetry", "run"]

