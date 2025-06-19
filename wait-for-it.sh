#!/usr/bin/env bash

# wait-for-it.sh

host=$1
shift
cmd="$@"

echo "Waiting for $host..."

while ! nc -z ${host}; do
  sleep 1
done

echo "$host is up. Executing command..."
exec $cmd
