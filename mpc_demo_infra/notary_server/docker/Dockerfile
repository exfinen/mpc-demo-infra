FROM ubuntu:24.04

SHELL ["/bin/bash", "-c"]
ENV PATH="/root/.cargo/bin:${PATH}:/root/tlsn/notary/target/release"
ARG NOTARY_IP="127.0.0.1"
ENV NOTARY_IP=${NOTARY_IP}

ENV DOCKERFILE_DIR="./mpc_demo_infra/notary_server/docker"

WORKDIR /root

RUN apt-get update && apt-get install -y curl git build-essential git libgmp-dev libntl-dev libsodium-dev libssl-dev libtool pkg-config libmpfr-dev libmpc-dev \
    && apt-get clean

# Install rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Build notary server
COPY tlsn /root/tlsn/
RUN cd tlsn/notary/server \
    && cargo build --release \
    && cp -R fixture ../target/release

# Generate self-signed certificate 
COPY $DOCKERFILE_DIR/openssl.cnf /root/tlsn/notary/server/fixture/tls/

# Copy config and cert files to release directory
RUN cp -R /root/tlsn/notary/server/fixture /root/tlsn/notary/target/release/
RUN cp -R /root/tlsn/notary/server/config /root/tlsn/notary/target/release/

#COPY $DOCKERFILE_DIR/ssl_certs/notary.crt /root/tlsn/notary/target/release/fixture/tls/
#COPY $DOCKERFILE_DIR/ssl_certs/notary.key /root/tlsn/notary/target/release/fixture/tls/

COPY $DOCKERFILE_DIR/config.yaml /root/tlsn/notary/target/release/config/

WORKDIR /root/tlsn/notary/target/release
EXPOSE 8003

CMD ["notary-server"]

