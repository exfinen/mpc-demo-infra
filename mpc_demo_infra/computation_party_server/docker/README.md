# Running Computation Party Server

## Set up procedure
### Assumptions
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
 
### Common configuration
1. Edit `mpc_demo_infra/computation_party_server/docker/.env.party` as follows:
   ```
   PARTY_HOSTS=["prod-party-0.mpcstats.org","prod-party-1.mpcstats.org","prod-party-2.mpcstats.org"]
   PARTY_PORTS=["8006","8007","8008"]
   ```

   ```
   COORDINATION_SERVER_URL=https://prod-coord.mpcstats.org:8005
   ```

### Per-server configuration
For each computation party server, do the following replacing %PORT% and %PARTY_ID% with those of the server to be configured.

1. If you're to use:
   - `https`: 
     1. Add `pem` files for your https domain to `mpc_demo_infra/computation_party_server/docker/ssl_certs` directory.
     2. Update the `PRIVKEY_PEM_PATH` and `FULLCHAIN_PEM_PATH` in `mpc_demo_infra/data_consumer_api/docker/.env.party`. The paths should be relative to the repository root.
   - `http`
     1. Update the `PARTY_WEB_PROTOCL` in `mpc_demo_infra/computation_party_server/docker/.env.party` as follows:
        ```
        PARTY_WEB_PROTOCOL=http
        ``` 

2. Update the following line in `mpc_demo_infra/computation_party_server/docker/Dockerfile`
   ```
   EXPOSE %PORT%
   ```
   2. Update the following line in `mpc_demo_infra/computation_party_server/docker/.env.party`
   ```
   PARTY_ID=%PARTY_ID%
   ``` 

   ```
   PORT=%PORT%
   ```

## Running the server
```bash
docker build -t party .
docker run -it -p %PORT%:%PORT% party 
```

