#!/bin/sh
set -eu
cd "$(dirname "$0")"
uv sync
uv run python -c 'from gi.repository import GLib; import gi; gi.require_version("Gst", "1.0"); from gi.repository import Gst; Gst.init(None); print(Gst.version_string())'
for element in appsrc jpegdec videoconvert x264enc h264parse mp4mux; do
    gst-inspect-1.0 "$element" >/dev/null
done
