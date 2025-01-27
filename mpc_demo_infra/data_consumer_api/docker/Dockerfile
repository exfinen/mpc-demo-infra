FROM ubuntu:24.04

SHELL ["/bin/bash", "-c"]
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /root

RUN apt-get update && apt-get install -y python3 python3-venv python3-pip pipx git libgmp-dev libntl-dev libsodium-dev libssl-dev libtool pkg-config libmpfr-dev libmpc-dev \
    && apt-get clean \
    && pipx install poetry \
    && pipx ensurepath

# Install mpc-demo-infra
# RUN git clone https://github.com/ZKStats/mpc-demo-infra.git \
#     && cd mpc-demo-infra \
#     && PYTHON_KEYRING_BACKEND=keyring.backends.fail.Keyring poetry install
RUN git clone https://github.com/exfinen/mpc-demo-infra.git \
    && cd mpc-demo-infra \
    && git fetch \
    && git checkout add-docker-compose \
    && PYTHON_KEYRING_BACKEND=keyring.backends.fail.Keyring poetry install

COPY .env.consumer_api /root/mpc-demo-infra/
COPY ssl_certs/ /root/mpc-demo-infra/ssl_certs/

WORKDIR /root/mpc-demo-infra
EXPOSE 8004

ENTRYPOINT ["poetry", "run"]
CMD ["consumer-api-run"]

