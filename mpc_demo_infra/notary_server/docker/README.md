# Running Notary Server

## Configring server
1. Copy the private key for the HTTPS domain as `cert_privkey.pem` into `mpc_demo_infra/notary_server/docker/ssl_certs` directory
2. Replace `notary.key` if necessary
3. If you need to change the port that the notary server listens to:
   1. Update the following line in `mpc_demo_infra/notary_server/docker/Dockerfile`
   ```
   EXPOSE 8003
   ```
   2. Update the following line in `mpc_demo_infra/notary_server/docker/config.yaml`
   ```
   server:
     ...
     port: 8003
   ```

## Running the server
```bash
docker build -t notary .
docker run -it -p 8003:8003 notary
```

