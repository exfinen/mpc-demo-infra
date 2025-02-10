# Running Computation Party Server with Docker

## Assumtion
This document assumes that each computation party server runs on a separate machine.

## Common preparation
1. Clone the `MP-SPDZ` repository
   ```bash
   git clone git@github.com:ZKStats/MP-SPDZ.git
   ```

2. Create pem and key files
   ```bash
   cd MP-SPDZ
   ./Scripts/setup-ssl.sh 3
   ```

3. Copy the pem and key files to the `<mpc-demo-infra repository root>/computation_party_server/docker/` directory
   ```bash
   cp Player-Data/P*.{pem,key} <mp-demo-infra repository root>/mpc_demo_infra/computation_party_server/docker/
   ```

4. If you intend to use HTTPS,
   1. Set `PARTY_WEB_PROTOCOL` to `https`
   1. Rename the private key and certificate files of your domain as `privkey.pem` and `fullchain.pem` respectively and add them to `mpc_demo_infra/computation_party_server/docker/ssl_certs` directory.

5. Edit `mpc_demo_infra/computation_party_server/docker/.env.party`:
   1. Set the hostnames or IP addresses of the three computation party servers to `PARTY_HOSTS` e.g.:
   ```
   PARTY_HOSTS=["123.123.123.1","123.123.123.2","123.123.123.3"]
   ```
   2. Set the `COORDINATION_SERVER_URL` to the URL of the coordination server. For example, if the coordination server is running on `123.123.123.100` and HTTP is being used, you would set it as follows:
   ```
   COORDINATION_SERVER_URL=http://123.123.123.100:8005
   ```

## Configuring each server
Three computation party servers are required for the MPC scheme used in the demo infra. Each server should be configured with a unique party ID (0, 1, or 2).

1. Edit `mpc_demo_infra/computation_party_server/docker/.env.party`:
   `PARTY_ID`: Set the party ID assigned to the server.

## Running the servers
On each party’s machine, follow below steps:

1. Move to the Docker directory:
```bash
cd mpc-demo-infra/mpc_demo_infra/computation_party_server/docker
```

2. Run the following commands, replacing %PORT% and %PARTY_ID%. Party 0, Party 1, and Party 2 should use ports 8005, 8006, and 8007, respectively.
```bash
export PORT=%PORT%
export PARTY_ID=%PARTY_ID%
export NUM_PARTIES=3
docker build --build-arg PORT=${PORT} --build-arg PARTY_ID=${PARTY_ID} --build-arg NUM_PARTIES=${NUM_PARTIES} -t party .
docker run --init -it -v party-data:/root/MP-SPDZ/ -p 8000-8100:8000-8100 -e PARTY_ID=${PARTY_ID} party
```

