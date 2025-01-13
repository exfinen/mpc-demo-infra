# Running Coordination Server

## Assumptions
1. 3-party computation is to be run.
2. Computation party server addresses and ports are:
| Party ID | Address | Port |
|----------|---------|------|
| 0 | prod-party-0.mpcstats.org | 8006 |
| 1 | prod-party-1.mpcstats.org | 8007 |
| 2 | prod-party-2.mpcstats.org | 8008 |

## Configuring the server
Edit `mpc_demo_infra/coordination_server/docker/.env.coord` as needed.

If `PARTY_WEB_PROTOCOL` is set to `https`, the following configuration will be necessary:
1. Add the `privkey.pem` and `fullchain.pem= files for your HTTPS domain to the `mpc_demo_infra/computation_party_server/docker/ssl_certs` directory.
2. Update the following variables in the `mpc_demo_infra/data_consumer_api/docker/.env.party file`:
   - `PRIVKEY_PEM_PATH`: Path to your private key PEM file.
   - `FULLCHAIN_PEM_PATH`: Path to your full chain PEM file.
   Ensure the paths are relative to the repository root.

## Running the server

```bash
cd /home/ubuntu/mpc-demo-infra/mpc_demo_infra/coordination_server/docker/
docker build -t coord .
docker run --init -it -v coord-data:/root/mpc-demo-infra -p 8005-8100:8005-8100 coord
```

