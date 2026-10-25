export default {
  template: '<img :src="url" alt="Live camera preview" @load="loaded" @error="retry" />',
  props: { src: String, fps: Number },
  data() {
    return { url: undefined, timer: null, started: 0, stopped: false };
  },
  mounted() {
    // NiceGUI initializes path_prefix during the parent app's mount.
    this.schedule(0);
  },
  beforeUnmount() {
    this.stopped = true;
    clearTimeout(this.timer);
  },
  methods: {
    requestFrame() {
      this.started = performance.now();
      const prefix = this.src.startsWith('/') ? (window.path_prefix || '') : '';
      const separator = this.src.includes('?') ? '&' : '?';
      this.url = `${prefix}${this.src}${separator}v=${this.started}`;
    },
    schedule(delay) {
      if (!this.stopped) this.timer = setTimeout(() => this.requestFrame(), delay);
    },
    loaded() {
      // Wait for this JPEG to load before replacing its URL. Updating a QImg
      // faster than the connection can load frames continually cancels loads.
      this.schedule(Math.max(0, 1000 / this.fps - (performance.now() - this.started)));
    },
    retry() {
      this.schedule(500);
    },
  },
};
