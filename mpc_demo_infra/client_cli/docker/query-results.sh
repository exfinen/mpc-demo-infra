#!/bin/bash

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

docker run -it mpcstats/client_cli:$TAG client-query

