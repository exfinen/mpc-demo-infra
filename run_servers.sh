#!/bin/bash

set -e

print_usage() {
    echo "Usage: ./run_servers.sh [--notary-only]"
    echo "Options:"
    echo "  --notary-only: Start Notary Server only"
    echo "  No option: Start all servers"
}

start_notary_only=false

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --notary-only)
      start_notary_only=true
      ;;
    *)
      print_usage
      exit 1
      ;;
  esac
  shift
done

# Kill any existing processes if they exist
pkill -f "poetry run coord-run" || true
pkill -f "PARTY_ID=0 poetry run party-run" || true
pkill -f "PARTY_ID=1 poetry run party-run" || true
pkill -f "PARTY_ID=2 poetry run party-run" || true
pkill -f "poetry run consumer-api-run" || true
pkill -f "notary-server" || true

if [ -d "venv" ]; then
  source venv/bin/activate
fi

# Array to store PIDs
pids=()

# Function to kill all background processes when script terminates
cleanup() {
  echo "Shutting down all servers..."
  for pid in "${pids[@]}"; do
    kill $pid 2>/dev/null || true
  done
  exit
}

# Set trap for SIGINT (Ctrl+C)
trap cleanup SIGINT

if [ "$start_notary_only" = false ]; then
  echo "Starting Coordination Server..."
  poetry run coord-run &
  pids+=($!)

  echo "Starting Computation Party Servers..."
  PORT=8006 PARTY_ID=0 poetry run party-run &
  pids+=($!)
  PORT=8007 PARTY_ID=1 poetry run party-run &
  pids+=($!)
  PORT=8008 PARTY_ID=2 poetry run party-run &
  pids+=($!)

  echo "Starting Data Consumer API Server..."
  poetry run consumer-api-run &
  pids+=($!)
fi

echo "Starting Notary Server..."
pushd ./tlsn/notary/target/release
./notary-server &
notary_pid=$!
popd
pids+=($notary_pid)

echo "All requested servers have started. Press Ctrl+C to stop the servers."
echo "Running PIDs: ${pids[@]}"

# Wait indefinitely until Ctrl+C is pressed
wait

