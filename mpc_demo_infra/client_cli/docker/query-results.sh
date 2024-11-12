#!/bin/bash

if [[ "$OSTYPE" == "darwin"* ]]; then
    TAG="latest-arm64"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    TAG="latest-amd64"
else
    echo "Unsupported operating system: $OSTYPE"
    exit 1
fi

docker run -it mpcstats/client_cli:$TAG client-query

