#!/bin/bash
# Run a command as a sandbox user, in a fresh login-like session with that
# user's own D-Bus session bus and GNOME Keyring (unlocked with the user's
# keyring password). The keyring is stored in the user's home folder, so it
# persists between sessions.
# Usage: run_as.sh USER COMMAND...
user="$1"; shift
cmd="$(printf '%q ' "$@")"
exec su - "$user" -c "dbus-run-session -- bash -c 'printf %s keyring-$user | gnome-keyring-daemon --unlock --components=secrets >/dev/null 2>&1; $cmd'"
