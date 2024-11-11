#!/bin/bash

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <voucher> <api-key> <api-secret>"
    exit 1
fi
docker run -it client_cli client-share-data $1 $2 $3

