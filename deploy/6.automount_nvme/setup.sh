sudo mkdir -p /home/pi/nvme

ENTRY='/dev/nvme0n1p2  /home/pi/nvme  ntfs  defaults  0  0'

grep -Fxq "$ENTRY" /etc/fstab || echo "$ENTRY" | sudo tee -a /etc/fstab >/dev/null

sudo systemctl daemon-reload

sudo mount -a
