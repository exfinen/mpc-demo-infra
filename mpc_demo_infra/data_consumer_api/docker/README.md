# Running Data Consumer API Server

## Setting up
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

3. In order to change the port Data Consumer API server listens to:
   1. Update the following line in `mpc_demo_infra/data_consumer_api/docker/Dockerfile`
   ```
   EXPOSE 8004
   ```
   2. Update the following line in `mpc_demo_infra/data_consumer_api/docker/.env.consumer_api`
   ```
   PORT=8004
   ```

## Running the server
```bash
docker build -t consumer_api .
docker run -it -p 8004:8004 consumer_api
```

