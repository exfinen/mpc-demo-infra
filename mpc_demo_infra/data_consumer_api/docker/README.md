# Running Data Consumer API Server

## Configring server
1. Edit the following parameters in `mpc_demo_infra/data_consumer_api/docker/.env.consumer_api` to suit your need:
    - COORDINATION_SERVER_URL
    - PARTY_HOSTS
2. If you intend to use HTTPS,
     1. Set `PARTY_WEB_PROTOCOL` to `https`
     1. Rename the private key and certificate files of your domain as `privkey.pem` and `fullchain.pem` respectively and add them to `mpc_demo_infra/data_consumer_api/docker/ssl_certs` directory.

## Running the server
```bash
docker build -t data_consumer_api .
docker run --init -it -p 8004:8004 data_consumer_api
```

