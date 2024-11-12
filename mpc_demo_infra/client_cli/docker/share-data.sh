#!/bin/bash

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <voucher> <binance-api-key> <binance-api-secret>"
    exit 1
fi

if [[ "$OSTYPE" == "darwin"* ]]; then
    TAG="latest-arm64"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    TAG="latest-amd64"
else
    echo "Unsupported operating system: $OSTYPE"
    exit 1
fi

docker run -it mpcstats/client_cli:$TAG client-share-data $1 $2 $3

