#!/bin/bash

if [[ "$OSTYPE" == "darwin"* ]]; then
    TAG="latest-arm64"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    TAG="latest-amd64"
else
    TAG="latest"
fi

docker run -it mpcstats/client_cli:$TAG client-query

