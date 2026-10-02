sudo cp 99-kiosk-input.rules /etc/udev/rules.d/99-kiosk-input.rules

sudo udevadm control --reload-rules
sudo udevadm trigger
sudo systemctl restart kiosk.service


