FROM ubuntu:24.04

SHELL ["/bin/bash", "-c"]
ENV PATH="/root/.cargo/bin:${PATH}:/root/tlsn/notary/target/release"

WORKDIR /root

RUN apt-get update && apt-get install -y curl git build-essential git libgmp-dev libntl-dev libsodium-dev libssl-dev libtool pkg-config libmpfr-dev libmpc-dev \
    && apt-get clean

# Install rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Build notary server
RUN git clone https://github.com/ZKStats/tlsn.git \
    && cd tlsn/notary/server \
    && git checkout mpspdz-compat-binance \
    && cargo build --release \
    && cp -R fixture ../target/release

# Copy config file and keys
COPY config.yaml /root/tlsn/notary/target/release/config/
COPY ssl_certs/cert_privkey.pem /root/tlsn/notary/target/release/keys/
COPY notary.key /root/tlsn/notary/target/release/fixture/notary/

WORKDIR /root/tlsn/notary/target/release
EXPOSE 8003

CMD ["notary-server"]

