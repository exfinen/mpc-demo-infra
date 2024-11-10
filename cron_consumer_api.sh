#!/bin/bash

CALL_EVERY_N_SECONDS=120

while true; do
    echo "Updating cache at $(date)"
    curl -s "https://client-api.mpcstats.org:8004/query-computation"
    if [ $? -eq 0 ]; then
        echo "Cache update successful"
    else
        echo "Cache update failed"
    fi
    sleep $CALL_EVERY_N_SECONDS
done
