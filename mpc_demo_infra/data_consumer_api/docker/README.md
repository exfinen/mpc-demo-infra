# Running Data Consumer API Server

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
 
## Configring server
1. Edit `mpc_demo_infra/data_consumer_api/docker/.env.consumer_api` according to your server configuraiton.
2. If you're to use:
   - `https`: 
     1. Add `pem` files for your https domain to `mpc_demo_infra/data_consumer_api/docker/ssl_certs` directory.
     2. Update the `PRIVKEY_PEM_PATH` and `FULLCHAIN_PEM_PATH` in `mpc_demo_infra/data_consumer_api/docker/.env.consumer_api`. The paths should be relative to the repository root.
   - `http`
     1. Update the `PARTY_WEB_PROTOCL` in `mpc_demo_infra/data_consumer_api/docker/.env.consumer_api` as follows:
        ```
        PARTY_WEB_PROTOCOL=http
        ``` 

3. In order to change the port that the data consumer api server listens to:
   1. Update the following line in `mpc_demo_infra/data_consumer_api/docker/Dockerfile`
   ```
   EXPOSE 8004
   ```
   2. Update the following line in `mpc_demo_infra/data_consumer_api/docker/.env.consumer_api`
   ```
   PORT=8004
   ```

4. Update the coordination server address in `mpc_demo_infra/computation_party_server/docker/.env.consumer_api` as follows:
   ```
   COORDINATION_SERVER_URL=https://prod-coord.mpcstats.org:8005
   ```

## Running the server
```bash
docker build -t consumer_api .
docker run --init -it -p 8004:8004 consumer_api
```

