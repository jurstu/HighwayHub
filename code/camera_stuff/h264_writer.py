"""Decode camera JPEGs and encode software H.264 into MP4 using GStreamer."""

from fractions import Fraction

from .gstreamer import Gst, check_bus, init_gst
from .jpeg_frame import JpegFrame


class H264VideoWriter:
    def __init__(self, path, fps: float, size: tuple[int, int], *, bitrate_kbps: int):
        if any(dimension <= 0 or dimension % 2 for dimension in size):
            raise OSError('H.264 recording requires positive, even frame dimensions')
        init_gst()
        self._pipeline = None
        self._frames = 0
        self._rate = Fraction(fps).limit_denominator(1001)
        self._size = size
        # Drop old JPEGs before decoding if the CPU falls behind. Capture and
        # preview never wait for encoding, and timestamps retain elapsed time.
        pipeline = Gst.parse_launch(
            'appsrc name=jpeg_source format=time is-live=true block=false emit-signals=false '
            'max-buffers=2 max-bytes=0 leaky-type=downstream '
            '! jpegdec ! videoconvert ! video/x-raw,format=I420 '
            f'! x264enc name=h264_encoder threads=3 speed-preset=ultrafast '
            f'tune=zerolatency bitrate={bitrate_kbps} '
            f'key-int-max={max(1, round(fps))} '
            '! video/x-h264,profile=constrained-baseline ! h264parse '
            # Write fragments as we go; avoid buffering the entire clip or
            # copying it into a faststart file when recording stops.
            '! mp4mux fragment-duration=1000 ! filesink name=output sync=false')
        self._pipeline = pipeline
        try:
            self._source = pipeline.get_by_name('jpeg_source')
            self._source.set_property('caps', Gst.Caps.from_string(
                f'image/jpeg,width={size[0]},height={size[1]},framerate={self._rate.numerator}/{self._rate.denominator}'))
            pipeline.get_by_name('output').set_property('location', str(path))
            self._bus = pipeline.get_bus()
            if pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
                check_bus(self._bus)
                raise OSError('Could not start the H.264 recording pipeline')
        except Exception:
            pipeline.set_state(Gst.State.NULL)
            self._pipeline = None
            raise

    def write(self, frame: JpegFrame):
        check_bus(self._bus)
        if self._pipeline is None:
            raise OSError('H.264 recording is closed')
        if (frame.width, frame.height) != self._size:
            raise ValueError('JPEG dimensions changed')
        buffer = Gst.Buffer.new_wrapped(frame.data)
        scale = Gst.SECOND * self._rate.denominator
        buffer.pts = buffer.dts = self._frames * scale // self._rate.numerator
        buffer.duration = (self._frames + 1) * scale // self._rate.numerator - buffer.pts
        if self._source.emit('push-buffer', buffer) != Gst.FlowReturn.OK:
            check_bus(self._bus)
            raise OSError('Could not write a JPEG packet')
        self._frames += 1

    def close(self):
        pipeline, self._pipeline = self._pipeline, None
        if pipeline is None:
            return
        try:
            if self._source.emit('end-of-stream') != Gst.FlowReturn.OK:
                raise OSError('Could not finalize the H.264 recording')
            message = self._bus.timed_pop_filtered(3 * Gst.SECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)
            if message is None:
                raise OSError('Timed out finalizing the H.264 recording')
            if message.type == Gst.MessageType.ERROR:
                error, _ = message.parse_error()
                raise OSError(error.message)
        finally:
            pipeline.set_state(Gst.State.NULL)
