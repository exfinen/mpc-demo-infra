#!/bin/bash

set -e 

echo "Starting all servers..."

if [ -d "venv" ]; then
  source venv/bin/activate
fi

# Start Coordination Server
poetry run coord-run &
coord_pid=$!

# Start Party 0 Computation Party Server
PORT=8006 PARTY_ID=0 poetry run party-run &
p0_pid=$!

# Start Party 1 Computation Party Server
PORT=8007 PARTY_ID=1 poetry run party-run &
p1_pid=$!

# Start Party 2 Computation Party Server
PORT=8008 PARTY_ID=2 poetry run party-run &
p2_pid=$!

# Start Data Consumer API Server
poetry run consumer-api-run &
consumer_pid=$!

# Start Notary Server
pushd ../tlsn/notary/target/release
./notary-server &
notary_pid=$!
popd

wait
echo "All servers started"

# Create shutdown-all-servers.sh
cat << EOF > shutdown-all-servers.sh
#!/bin/bash

echo "Stopping all servers..."
for pid in "$coord_pid" "$p0_pid" "$p1_pid" "$p2_pid" "$consumer_pid" "$notary_pid"; do
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
  fi
done
echo "All servers stopped."
EOF

