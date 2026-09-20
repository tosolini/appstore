#!/bin/sh
set -e

# The container may start as root (docker-compose sets user: "0") to fix
# the ownership of bind-mounted volumes like ./data, which are owned by the
# host user. After chowning, we drop privileges to the non-root app user.
if [ "$(id -u)" = "0" ]; then
  chown -R appuser:appuser /app/data /app/cache 2>/dev/null || true
  exec setpriv --reuid=10001 --regid=10001 --init-groups "$@"
fi

exec "$@"