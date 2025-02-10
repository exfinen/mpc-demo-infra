# Running Notary Server with Docker

## Using HTTPS for your domain
To run Notary Server for your domain, replace `notary.key` and `notary.crt` in the `mpc_demo_infra/notary_server/docker/ssl_certs` directory with your domain's private key and certificate files respectively.

## Running the server
Run the following commands, replacing %NOTARY_IP% with the IP address of the server on which the Notary server runs:

```bash
docker build  --build-arg NOTARY_IP=%NOTARY_IP% -t notary .
docker run --init -it -p 8003:8003 notary
```

