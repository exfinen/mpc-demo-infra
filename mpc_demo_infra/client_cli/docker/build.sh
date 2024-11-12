#!/bin/bash

if [[ "$OSTYPE" == "darwin"* ]]; then
  if [[ "$(uname -m)" == "x86_64" ]]; then
    echo "Pulling amd64 image..."
    docker pull mpcstats/client_cli:latest-amd64
  elif [[ "$(uname -m)" == "arm64" ]]; then
    echo "Pulling arm64 image..."
    docker pull mpcstats/client_cli:latest-arm64
  else
    echo "Building image..."
    docker build -t client_cli .
  fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  echo "Pulling amd64 image..."
  docker pull mpcstats/client_cli:latest-amd64
else
  echo "Building image..."
  docker build -t client_cli .
fi

echo 'Done'

