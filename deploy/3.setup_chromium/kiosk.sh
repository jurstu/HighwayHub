#!/bin/bash

unset DISPLAY
unset WAYLAND_DISPLAY


export XCURSOR_THEME=invisible
export XCURSOR_SIZE=24

exec cage -- chromium \
    --kiosk \
    --no-first-run \
    --disable-session-crashed-bubble \
    --password-store=basic \
    http://127.0.0.1:8080/main_navigation_screen
