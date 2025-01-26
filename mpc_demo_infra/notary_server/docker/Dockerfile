FROM ubuntu:24.04

SHELL ["/bin/bash", "-c"]
ENV PATH="/root/.cargo/bin:${PATH}:/root/tlsn/notary/target/release"
ARG COORD_IP="127.0.0.1"
ENV COORD_IP=${COORD_IP}

WORKDIR /root

RUN apt-get update && apt-get install -y curl git build-essential git libgmp-dev libntl-dev libsodium-dev libssl-dev libtool pkg-config libmpfr-dev libmpc-dev \
    && apt-get clean

# Install rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Build notary server
# RUN git clone https://github.com/ZKStats/tlsn.git \
#     && cd tlsn/notary/server u
#     && git checkout mpspdz-compat \
#     && cargo build --release \
#     && cp -R fixture ../target/release
RUN git clone https://github.com/exfinen/tlsn.git \
    && cd tlsn/notary/server \
    && git checkout turn-off-tls \
    && cargo build --release \
    && cp -R fixture ../target/release

RUN cp -R /root/tlsn/notary/server/fixture /root/tlsn/notary/target/release/
RUN cp -R /root/tlsn/notary/server/config /root/tlsn/notary/target/release/

COPY config.yaml /root/tlsn/notary/target/release/config/

# Generate self-signed certificate 
COPY openssl.cnf /root/tlsn/notary/server/fixture/tls/

WORKDIR /root/tlsn/notary/server/fixture/tls/
RUN sed -i "s/XXX/${COORD_IP}/" openssl.cnf
RUN openssl genpkey -algorithm RSA -out notary.key -pkeyopt rsa_keygen_bits:2048 \
    && openssl req -new -key notary.key -out request.csr -subj "/C=US/ST=State/L=City/O=Organization/OU=Department/CN=${COORD_IP}" \
    && openssl x509 -req -in request.csr -signkey notary.key -out notary.crt -days 365 -extfile openssl.cnf -extensions v3_req 

WORKDIR /root/tlsn/notary/target/release
EXPOSE 8003

CMD ["notary-server"]

