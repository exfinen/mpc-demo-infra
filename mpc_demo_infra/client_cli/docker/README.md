# MPC Demo Client

## Requirement
- Docker

## Preparation
Build a Docker image for the MPC Demo Client as follows:

```
cd mpc-demo-infra/client_cli/docker
./build.sh
```

## How to share your data
You need to obtain a voucher to share your data

```
cd mpc-demo-infra/client_cli/docker
./share-data.sh <voucher> <api-key> <api-secret>
```

## How to query the results of computation based on shared data
```
cd mpc-demo-infra/client_cli/docker
./query-results.sh
```

