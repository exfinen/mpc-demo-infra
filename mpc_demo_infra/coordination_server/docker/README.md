# Running Coordination Server with Docker

## Configuring the server
Edit `mpc_demo_infra/coordination_server/docker/.env.coord`:
1. Set the hostnames or IP addresses of the three computation party servers to:
```
PARTY_HOSTS=["party_0", "party_1", "party_2"]
```
2. If you intend to use HTTPS, update the following parameters:
   - `PARTY_WEB_PROTOCOL`: Set to `https`.
   - `PRIVKEY_PEM_PATH`: Path to your private key PEM file.
   - `FULLCHAIN_PEM_PATH`: Path to your full chain PEM file.
   The paths need to be relative to the repository root.

   Also add the `privkey.pem` and `fullchain.pem` files for your HTTPS domain to the `mpc_demo_infra/computation_party_server/docker/ssl_certs` directory.

## Running the server

```bash
cd ./mpc_demo_infra/coordination_server/docker/
docker build -t coord .
docker run --init -it -v coord-data:/root/mpc-demo-infra/ -p 8005-8100:8005-8100 coord
```

