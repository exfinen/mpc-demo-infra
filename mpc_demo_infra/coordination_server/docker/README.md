# Running Coordination Server with Docker

## Configuring the server
1. Edit the following parameters in `mpc_demo_infra/coordination_server/docker/.env.coord` to suit your need:
    - PARTY_HOSTS
2. If you intend to use HTTPS,
     1. Set `PARTY_WEB_PROTOCOL` to `https`
     1. Rename the private key and certificate files of your domain as `privkey.pem` and `fullchain.pem` respectively and add them to `mpc_demo_infra/data_consumer_api/docker/ssl_certs` directory.

## Running the server

```bash
cd ./mpc_demo_infra/coordination_server/docker/
docker build -t coord .
docker run --init -it -v coord-data:/root/mpc-demo-infra/ -p 8005-8100:8005-8100 coord
```

