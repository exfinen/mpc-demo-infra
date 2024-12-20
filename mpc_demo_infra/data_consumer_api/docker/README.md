# Installation steps

1. Edit `mpc_demo_infra/data_consumer_api/docker/.env.consumer_api` according to your server configuraiton
2. If you're to use `https`, add `pem` files for your https domain to `mpc_demo_infra/coordination_server/docker/ssl_certs 

3. Build Consumer API Docker image and run
   ```bash
   docker build -t consumer_api .
   docker run -it consumer_api
   ```

