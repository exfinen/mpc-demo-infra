FROM ubuntu:24.04

SHELL ["/bin/bash", "-c"]
ENV PATH="/root/.cargo/bin:/root/.local/bin:${PATH}"
ARG PORT=8006
ENV PORT=${PORT}
ARG PARTY_ID=0
ENV PARTY_ID=${PARTY_ID}

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
    && git checkout mpspdz-compat \
    && cd tlsn \
    && cargo build --release --example binance_verifier

# Install MP-SPDZ and generate party cert files
RUN git clone --recursive https://github.com/ZKStats/MP-SPDZ.git
COPY CONFIG.mine /root/MP-SPDZ
RUN cd MP-SPDZ \
    && git checkout demo_client \
    && make -j$(nproc) malicious-rep-ring-party.x \
    && Scripts/setup-ssl.sh 3 \
    && mv Player-Data/P${PARTY_ID}.* /root \
    && rm -f Player-Data/P*.{pem,key} \
    && mv /root/P${PARTY_ID}.* Player-Data

COPY .env.party /root/mpc-demo-infra/
COPY ssl_certs/ /root/mpc-demo-infra/ssl_certs/

RUN sed -i "s/^PORT=.*/PORT=${PORT}/" /root/mpc-demo-infra/.env.party \
    && sed -i "s/^PARTY_ID=.*/PARTY_ID=${PARTY_ID}/" /root/mpc-demo-infra/.env.party

ENV LD_LIBRARY_PATH="/root/MP-SPDZ"
WORKDIR /root/mpc-demo-infra
EXPOSE 8000-9000

ENTRYPOINT ["poetry", "run"]
CMD ["party-run"]

