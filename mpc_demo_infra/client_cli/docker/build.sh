#!/bin/bash

cp ../.env.client_cli .

echo "Building image..."
docker build -t client_cli .

echo 'Done'

