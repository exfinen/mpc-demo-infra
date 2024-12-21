# Running Computation Party Server

## Setting up
1. Edit `mpc_demo_infra/computation_party_server/docker/.env.party` according to your server configuraiton.
2. If you're to use:
   - `https`: 
     1. Add `pem` files for your https domain to `mpc_demo_infra/computation_party_server/docker/ssl_certs` directory.
     2. Update the `PRIVKEY_PEM_PATH` and `FULLCHAIN_PEM_PATH` in `mpc_demo_infra/data_consumer_api/docker/.env.party`. The paths should be relative to the repository root.
   - `http`
     1. Update the `PARTY_WEB_PROTOCL` in `mpc_demo_infra/computation_party_server/docker/.env.party` as follows:
        ```
        PARTY_WEB_PROTOCOL=http
        ``` 

3. In order to change the port Coordination server listens to:
   1. Update the following line in `mpc_demo_infra/computation_party_server/docker/Dockerfile`
   ```
   EXPOSE 800?
   ```
   2. Update the following line in `mpc_demo_infra/computation_party_server/docker/.env.party`
   ```
   PORT=800?
   ```

## Running the server
```bash
docker build -t party .
docker run -it -p 800?:800? party 
```


