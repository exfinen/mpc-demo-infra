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

# Install binance_verifier
RUN git clone https://github.com/ZKStats/tlsn.git \
    && cd tlsn \
    && git checkout mpspdz-compat-binance \
    && cd tlsn \
    && cargo build --release --example binance_verifier \
    && mv /root/tlsn/tlsn/target/release/examples/binance_verifier /root/tlsn/tlsn/examples/

COPY .env.coord /root/mpc-demo-infra/
COPY ssl_certs/ /root/mpc-demo-infra/ssl_certs/

WORKDIR /root/mpc-demo-infra
EXPOSE 8005

ENTRYPOINT ["poetry", "run"]
CMD ["coord-run"]
