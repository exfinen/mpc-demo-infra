#!/bin/bash

if [[ "$OSTYPE" == "darwin"* ]]; then
  echo "Pulling arm64 image..."
  docker pull mpcstats/client_cli:latest-arm64
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  echo "Pulling amd64 image..."
  docker pull mpcstats/client_cli:latest-amd64
else
  echo "Building image..."
  docker build -t client_cli .
fi

echo 'Done'

