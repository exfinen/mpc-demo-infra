#!/bin/sh

for port in 5577 5566 5567 5568; do
  lsof -i :${port}
  if [ $? -eq 0 ]; then
    # Get the PID of the process using the port and kill it
    pid=$(lsof -t -i :${port})
    kill $pid
  fi
done
