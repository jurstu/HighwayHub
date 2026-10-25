"""Shared GStreamer bindings (installed by deploy/0.install_stuff.sh and uv)."""

import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import GLib, Gst, GstVideo


def init_gst():
    if not Gst.is_initialized():
        Gst.init(None)


def check_bus(bus):
    message = bus.pop_filtered(Gst.MessageType.ERROR | Gst.MessageType.EOS)
    if message is not None:
        if message.type == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            raise OSError(f'{error.message} ({debug})')
        raise OSError('GStreamer stream ended')
