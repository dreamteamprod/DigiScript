#!/bin/sh
# Container entrypoint: fix ownership of the data directory left behind by
# older (root) images, then drop privileges and run the server.
set -eu

APP_USER=digiscript
DATA_DIR=/server/conf

if [ "$(id -u)" = "0" ]; then
    # Cheap check first: only walk the tree if the top-level directory or one of
    # the well-known files is not already owned by the app user.
    app_uid="$(id -u "$APP_USER")"
    needs_chown=0
    for path in "$DATA_DIR" "$DATA_DIR/digiscript.json" "$DATA_DIR/digiscript.sqlite"; do
        if [ -e "$path" ] && [ "$(stat -c %u "$path")" != "$app_uid" ]; then
            needs_chown=1
        fi
    done
    if [ "$needs_chown" = "1" ]; then
        echo "Updating ownership of $DATA_DIR for user $APP_USER (one-time upgrade step)"
        chown -R "$APP_USER:$APP_USER" "$DATA_DIR"
    fi
    exec gosu "$APP_USER" python3 main.py "$@"
fi

# Started with --user (or rootless): nothing to chown, just run.
exec python3 main.py "$@"
