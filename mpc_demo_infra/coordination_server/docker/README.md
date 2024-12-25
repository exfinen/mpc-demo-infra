# Running Coordination Server

## Assumptions
2. 3-party computation is to be run.
3. Computation party server addresses and ports are:
| Party ID | Address | Port |
|----------|---------|------|
| 0 | prod-party-0.mpcstats.org | 8006 |
| 1 | prod-party-1.mpcstats.org | 8007 |
| 2 | prod-party-2.mpcstats.org | 8008 |

## Conguring server
1. Edit `mpc_demo_infra/coordination_server/docker/.env.coord` according to your server configuraiton.
2. If you're to use:
   - `https`: 
     1. Add `pem` files for your https domain to `mpc_demo_infra/coordination_server/docker/ssl_certs` directory.
     2. Update the `PRIVKEY_PEM_PATH` and `FULLCHAIN_PEM_PATH` in `mpc_demo_infra/data_consumer_api/docker/.env.coord`. The paths should be relative to the repository root.
   - `http`
     1. Update the `PARTY_WEB_PROTOCL` in `mpc_demo_infra/coordination_server/docker/.env.coord` as follows:
        ```
        PARTY_WEB_PROTOCOL=http
        ``` 

3. In order to change the port Coordination server listens to:
   1. Update the following line in `mpc_demo_infra/coordination_server/docker/Dockerfile`
   ```
   EXPOSE 8005
   ```
   2. Update the following line in `mpc_demo_infra/coordination_server/docker/.env.coord`
   ```
   PORT=8004
   ```

## Running the server
```bash
docker build -t coord .
docker run --init -it -p 8005:8005 coord
```


