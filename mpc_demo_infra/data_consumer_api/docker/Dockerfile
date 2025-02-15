FROM ubuntu:24.04

SHELL ["/bin/bash", "-c"]
ENV PATH="/root/.local/bin:${PATH}"

ENV DOCKERFILE_DIR="./mpc_demo_infra/data_consumer_api/docker"

RUN apt-get update && apt-get install -y python3 python3-venv python3-pip pipx git libgmp-dev libntl-dev libsodium-dev libssl-dev libtool pkg-config libmpfr-dev libmpc-dev \
    && apt-get clean \
    && pipx install poetry \
    && pipx ensurepath

WORKDIR /root

# Install mpc-demo-infra
COPY . .
RUN cd mpc-demo-infra \
    && PYTHON_KEYRING_BACKEND=keyring.backends.fail.Keyring poetry install

COPY $DOCKERFILE_DIR/.env.consumer_api /root/mpc-demo-infra/
COPY $DOCKERFILE_DIR/ssl_certs/ /root/mpc-demo-infra/ssl_certs/

WORKDIR /root/mpc-demo-infra
EXPOSE 8004

ENTRYPOINT ["poetry", "run"]
CMD ["consumer-api-run"]

