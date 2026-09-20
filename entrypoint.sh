#!/bin/sh
set -e

APP_UID=10001
APP_GID=10001

# The container should start as root (docker-compose sets user: "0") to fix
# the ownership of bind-mounted volumes like ./data, which the host may create
# as root. After chowning, we drop privileges to the non-root app user.
if [ "$(id -u)" = "0" ]; then
  chown -R appuser:appuser /app/data /app/cache 2>/dev/null || true
  exec setpriv --reuid=$APP_UID --regid=$APP_GID --init-groups "$@"
fi

# Running as non-root (e.g. prod compose without user: "0"): the entrypoint
# cannot chown. Warn clearly if data/cache dirs are not writable, so a
# root-owned ./data is easy to spot in the logs.
if [ ! -w /app/data ] || [ ! -w /app/cache ]; then
  echo "WARNING: /app/data or /app/cache is not writable by uid $(id -u)." >&2
  echo "If ./data was created by root, either run 'sudo chown -R $APP_UID:$APP_GID ./data'" >&2
  echo "or start the container once with user: \"0\" so the entrypoint can chown it." >&2
fi

exec "$@"