# MPC Demo Client

## Requirement
- Docker

## Preparation
Build a Docker image for the MPC Demo Client as follows:

```
cd mpc-demo-infra/client_cli/docker
./build.sh
```

## How to Share Your Data
To share your data, you need to obtain a voucher. You will also need to have your Binance API key and API Secret ready to allow the demo client to access your ETH balance on Binance.

```
cd mpc-demo-infra/client_cli/docker
./share-data.sh <voucher> <binance-api-key> <binance-api-secret>
```

## How to query the results of computation based on data shared by participants
```
cd mpc-demo-infra/client_cli/docker
./query-results.sh
```

