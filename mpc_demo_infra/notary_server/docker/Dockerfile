FROM ubuntu:24.04

SHELL ["/bin/bash", "-c"]
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /root

RUN apt-get update && apt-get install -y curl git build-essential git libgmp-dev libntl-dev libsodium-dev libssl-dev libtool pkg-config libmpfr-dev libmpc-dev \
    && apt-get clean \
    && pipx install poetry \
    && pipx ensurepath

# Install rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

COPY config.yaml /root/tlsn/notary/server/config
COPY ssl_certs/ /root/tlsn/notary/server/keys/
COPY notary.key /root/tlsn/notary/server/fixture/notary

# Install notary server
RUN git clone https://github.com/ZKStats/tlsn.git \
    && cd tlsn/notary/server \
    && git checkout mpspdz-compat-binance \
    && cargo build --release

WORKDIR /root/tlsn/notary/target/release
EXPOSE 8003

CMD ["notary-server"]

