#!/bin/bash
# Run an app's self test and show its report.
# Passes when everything works (exit 0) or only the OS key store is missing
# (exit 2), as on build servers.
#
# Usage: packaging/check_self_test.sh APP [ARGS...]
set -uo pipefail
report="$(mktemp)"
"$@" --self-test-report "$report"
code=$?
cat "$report"
rm -f "$report"
if [ "$code" != 0 ] && [ "$code" != 2 ]; then
    echo "Self test failed with exit code $code"
    exit 1
fi
