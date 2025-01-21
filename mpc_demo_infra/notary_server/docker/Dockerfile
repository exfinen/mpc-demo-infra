FROM ubuntu:24.04

SHELL ["/bin/bash", "-c"]
ENV PATH="/root/.cargo/bin:${PATH}:/root/tlsn/notary/target/release"

WORKDIR /root

RUN apt-get update && apt-get install -y curl git build-essential git libgmp-dev libntl-dev libsodium-dev libssl-dev libtool pkg-config libmpfr-dev libmpc-dev \
    && apt-get clean

# Install rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Build notary server
# RUN git clone https://github.com/ZKStats/tlsn.git \
#     && cd tlsn/notary/server \
#     && git checkout mpspdz-compat-binance \
#     && cargo build --release \
#     && cp -R fixture ../target/release
RUN git clone https://github.com/exfinen/tlsn.git \
    && cd tlsn/notary/server \
    && git checkout turn-off-tls \
    && cargo build --release \
    && cp -R fixture ../target/release

# Copy config file
COPY config.yaml /root/tlsn/notary/target/release/config/

COPY /root/tlsn/notary/server/fixture/tls/rootCA.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates

#RUN cp /root/tlsn/notary/server/fixture/notary/notary.key /root/tlsn/notary/target/release/fixture/notary/

RUN if [ -f ssl_certs/cert_privkey.pem ]; then \
    mkdir -p /root/tlsn/notary/target/release/keys && \
    cp ssl_certs/cert_privkey.pem /root/tlsn/notary/target/release/keys/; \
    fi

WORKDIR /root/tlsn/notary/target/release
EXPOSE 8003

CMD ["notary-server"]

