Run the system packages before setting up the Python environment:

```sh
bash deploy/0.install_stuff.sh
bash deploy/1.uv_setup/1.setup.sh
```

The system installer supplies GStreamer, its Base/Good/Bad/Ugly plugins, introspection
data and development headers. `uv sync` builds PyGObject for the environment's
Python interpreter. PyGObject stays below 3.51 to support the older GI development
packages available on Debian/Raspberry Pi OS Bookworm as well as Ubuntu 24.04.

Capture uses `v4l2src`, `tee`, `appsink`, `valve`, `jpegdec` and `videoconvert`.
Recording uses `appsrc ! jpegdec ! videoconvert ! x264enc ! h264parse ! mp4mux`
to encode software H.264 into `.mp4` files. `x264enc` comes from Ugly plugins;
`h264parse` comes from Bad plugins. Setup checks these elements are available.
OpenCV remains for recording-library thumbnails.

`CameraRecorder(bitrate_kbps=6000)` sets the target bitrate (default 6 Mbps,
roughly 11 MB per 15 seconds, depending on the scene). The `ultrafast` preset
and `zerolatency` tuning minimize encoder CPU work and buffering. The encoder
uses three worker threads to limit CPU contention on the Pi 5's four cores;
no hardware encoder or decoder is used. A two-frame
queue drops older JPEGs if encoding cannot keep up, without blocking capture
or the browser preview. MP4 fragments are written every second and finalized
on stop. Existing AVI recordings remain available in the video library.

The browser continues to receive original camera JPEGs without re-encoding.
Verify the achievable recording rate on the Pi itself; desktop test throughput
does not establish Pi performance.
