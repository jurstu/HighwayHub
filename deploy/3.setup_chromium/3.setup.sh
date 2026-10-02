
set -ex

sudo apt install cage chromium

sudo cp kiosk.sh /usr/local/bin/

sudo cp kiosk.service /etc/systemd/system/kiosk.service

sudo systemctl set-default multi-user.target

sudo systemctl disable --now getty@tty1.service

sudo systemctl daemon-reload

sudo systemctl enable kiosk.service
sudo systemctl restart kiosk.servicue
