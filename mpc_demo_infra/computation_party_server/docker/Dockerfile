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

# install binance_verifier
RUN git clone https://github.com/ZKStats/tlsn.git \
    && cd tlsn \
    && git checkout mpspdz-compat \
    && cd tlsn \
    && cargo build --release --example binance_verifier

# Install MP-SPDZ
RUN git clone https://github.com/ZKStats/MP-SPDZ.git \
    && cd MP-SPDZ \
    && git checkout demo_client \
    && make -j$(nproc) malicious-rep-ring-party.x

# export LD_LIBRARY_PATH=/home/ubuntu/MP-SPDZ

COPY .env.party /root/mpc-demo-infra/
COPY ssl_certs/ /root/mpc-demo-infra/ssl_certs/

ENV LD_LIBRARY_PATH="/root/MP-SPDZ:$LD_LIBRARY_PATH"
WORKDIR /root/mpc-demo-infra
EXPOSE 8006

ENTRYPOINT ["poetry", "run"]
CMD ["party-run"]

