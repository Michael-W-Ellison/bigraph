#!/bin/bash
# s.sh USER STEP ARGS... : run one scenario step as USER
u="$1"; shift
/srv/run_as.sh "$u" /srv/bigraph-venv/bin/python /srv/bigraph-scenario/step.py "$@" 2>&1 | grep -v "^dbus-daemon\|GNOME_KEYRING"
exit ${PIPESTATUS[0]}
