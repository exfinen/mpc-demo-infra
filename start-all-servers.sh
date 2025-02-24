#!/bin/bash

set -e 

./shutdown-all-servers.sh

if [ -d "venv" ]; then
  source venv/bin/activate
fi

echo "Staring Coordination Server..."
poetry run coord-run &

echo "Staring Computation Party Servers..."
PORT=8006 PARTY_ID=0 poetry run party-run &
PORT=8007 PARTY_ID=1 poetry run party-run &
PORT=8008 PARTY_ID=2 poetry run party-run &

echo "Staring Data Consumer API Server..."
poetry run consumer-api-run &

echo "Staring Notary Server..."
pushd ../tlsn/notary/target/release
./notary-server &
popd

echo "All servers started"

