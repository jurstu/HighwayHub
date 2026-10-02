#!/bin/bash

unset DISPLAY
unset WAYLAND_DISPLAY

export XCURSOR_THEME=invisible
export XCURSOR_SIZE=24

# Wait for Cage's Wayland compositor to start, then rotate DSI.
(
    sleep 5
    export WAYLAND_DISPLAY=wayland-0
    wlr-randr --output DSI-2 --transform 90
) &

exec cage -- chromium \
    --kiosk \
    --no-first-run \
    --disable-session-crashed-bubble \
    --password-store=basic \
    http://127.0.0.1:8080/main_navigation_screen
