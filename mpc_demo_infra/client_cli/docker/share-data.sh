#!/bin/bash

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <voucher> <binance-api-key> <binance-api-secret>"
    exit 1
fi

if [[ "$OSTYPE" == "darwin"* ]]; then
    if [[ "$(uname -m)" == "x86_64" ]]; then
        TAG="latest-amd64"
    elif [[ "$(uname -m)" == "arm64" ]]; then
        TAG="latest-arm64"
    else
        TAG="latest"
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    TAG="latest-amd64"
else
    TAG="latest"
fi

docker run -it mpcstats/client_cli:$TAG client-share-data $1 $2 $3

