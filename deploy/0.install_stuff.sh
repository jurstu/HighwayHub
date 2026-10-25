sudo apt update

sudo apt install -y nload screen vim htop tmux

# GStreamer capture, software H.264/MP4 recording; headers for uv's PyGObject build.
sudo apt install -y \
    gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
    gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 \
    libgirepository1.0-dev libcairo2-dev pkg-config build-essential python3-dev


#sudo apt

curl -LsSf https://astral.sh/uv/install.sh | sh


