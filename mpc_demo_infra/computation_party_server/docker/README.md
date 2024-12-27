# Running Computation Party Server

## Assumptions
This document assumes that:
1. Coordinbation server URL is:
   ```
   https://prod-coord.mpcstats.org:8005
   ```
2. 3-party computation is to be run.
3. Computation party server addresses and ports are:
| Party ID | Address | Port |
|----------|---------|------|
| 0 | prod-party-0.mpcstats.org | 8006 |
| 1 | prod-party-1.mpcstats.org | 8007 |
| 2 | prod-party-2.mpcstats.org | 8008 |
 
## Configuring server
### Common configuration
1. Clone the `MP-SPDZ` repository
   ```bash
   git clone git@github.com:ZKStats/MP-SPDZ.git
   ```

2. Create certificates
   ```bash
   cd MP-SPDZ
   ./Scripts/setup-ssl.sh 3
   ```

3. Copy the certificates to the `<mpc-demo-infra repository root>/computation_party_server/docker/` directory
   ```bash
   cp Player-Data/P*.{pem,key} <mp-demo-infra repository root>/mpc_demo_infra/computation_party_server/docker/
   ```

4. Edit `mpc_demo_infra/computation_party_server/docker/.env.party` as follows:
   ```
   PARTY_HOSTS=["prod-party-0.mpcstats.org","prod-party-1.mpcstats.org","prod-party-2.mpcstats.org"]
   PARTY_PORTS=["8006","8007","8008"]
   ```

   ```
   COORDINATION_SERVER_URL=https://prod-coord.mpcstats.org:8005
   ```

### Per-server configuration

- Transport Protocol
If `PARTY_WEB_PROTOCOL` is set to `https`, the following configuration will be necessary:
1. Add the .pem files for your HTTPS domain to the `mpc_demo_infra/computation_party_server/docker/ssl_certs directory`.
2. Update the following variables in the `mpc_demo_infra/data_consumer_api/docker/.env.party file`:
   - `PRIVKEY_PEM_PATH`: Path to your private key PEM file.
   - `FULLCHAIN_PEM_PATH`: Path to your full chain PEM file.
   Ensure the paths are relative to the repository root.

- MPC Scheme
Different MPC schemes can be used for the computation party server.

To use a different MPC scheme:
1. Modify the following line in `mpc_demo_infra/computation_party_server/docker/Dockerfile`:
   ```
   && make -j$(nproc) malicious-rep-ring-party.x \
   ```
2. Add the following line to `mpc_demo_infra/computation_party_server/docker/.env.party`:
   ```
   MPSPDZ_PROTOCOL=<Protocol Name>
   ```
   The protocol name should be the name of the `.x` file generated in the previous step with `-party.x` suffix removed. i.e. `malicious-rep-ring` for `malicious-rep-ring-party.x`.

For the list of available schemes, refer to the `Protocols` section in the [MP-SPDZ README](https://github.com/ZKStats/MP-SPDZ?tab=readme-ov-file).

## Running the servers
To run the servers on each party’s host, follow these steps:

1. Navigate to the `mpc-demo-infra/mpc_demo_infra/computation_party_server/docker` directory:
```bash
cd mpc-demo-infra/mpc_demo_infra/computation_party_server/docker
```

2. Run the following commands, replacing %PORT% and %PARTY_ID% with the port and party ID for the server:
```bash
export PORT=%PORT%
export PARTY_ID=%PARTY_ID%
docker build --build-arg PORT=${PORT} --build-arg PARTY_ID=${PARTY_ID} -t party .
docker run --init -it -p 8000-8030:8000-8030 -e PARTY_ID=${PARTY_ID} party
```

