kill_all() {
  local name="$1"
  local substr="$2"

  while true; do
    local pids
    pids=$(ps aux \
      | grep "$substr" \
      | grep -v 'grep' \
      | awk '{print $2}' \
      | xargs
    )
    if [ -z "$pids" ]; then
      break
    fi

    kill -9 $pids
    echo "Killed $name ($pids)"
  done
}

kill_all "Coordination Server" "coord-run"
kill_all "Computation Party Servers" "party-run"
kill_all "Data Consumer API Server" "consumer-api-run"
kill_all "Notary Server" "notary-server"

