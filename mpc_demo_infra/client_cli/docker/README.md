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
./share-data.sh [voucher]
```

## How to query the sum of the shared data
```
cd mpc-demo-infra/client_cli/docker
./query-sum.sh
```

## How to query the mean of the shared data
```
cd mpc-demo-infra/client_cli/docker
./query-mean.sh
```

