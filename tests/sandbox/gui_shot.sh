#!/bin/bash
# Start the installed app on a virtual display, screenshot it, then close it.
# Usage: gui_shot.sh OUTPUT.png [TAB_INDEX]
out="$1"; tab="${2:-0}"
Xvfb :91 -screen 0 1100x800x24 >/dev/null 2>&1 &
xvfb=$!
sleep 1
export DISPLAY=:91
bigraph >/tmp/gui-$USER.log 2>&1 &
app=$!
for i in $(seq 1 30); do
    win=$(xdotool search --name "Bigraph Cryptography System" 2>/dev/null | head -1)
    [ -n "$win" ] && break
    sleep 0.5
done
sleep 2
# Dismiss any startup message box with Enter
xdotool key Return 2>/dev/null; sleep 1
if [ -n "$win" ] && [ "$tab" != 0 ]; then
    xdotool windowactivate --sync "$win" 2>/dev/null
    xdotool mousemove --window "$win" $((40 + 120 * tab)) 20 click 1; sleep 1
fi
import -window root "$out"
echo "window: ${win:-not found}"
cat /tmp/gui-$USER.log
kill $app 2>/dev/null; kill $xvfb 2>/dev/null
