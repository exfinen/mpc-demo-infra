kill_all() {
  local substr="$1"

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
    echo "Killed $pids that matched with '$substr'"
  done
}

kill_all "coord-run"
kill_all "party-run"
kill_all "consumer-api-run"
kill_all "notary-server"

