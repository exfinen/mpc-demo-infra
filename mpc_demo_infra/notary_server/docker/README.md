# Running Notary Server

## Configring server
1. Edit the following section of `mpc_demo_infra/notary_server/docker/config.yaml` according to your tls/key configuraiton:
   ```
   tls:
     enabled: true
     private-key-pem-path: "./keys/cert_privkey.pem"
     certificate-pem-path: "./fixture/tls/notary.crt"

   notary-key:
     private-key-pem-path: "./fixture/notary/notary.key"
     public-key-pem-path: "./fixture/notary/notary.pub"
   ```

2. If you need to change the port that the notary server listens to:
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

