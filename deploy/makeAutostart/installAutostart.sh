set -ex

sudo cp HighwayHub.service /etc/systemd/system
sudo cp startHighwayHub.sh ~/

sudo systemctl daemon-reload
sudo systemctl enable HighwayHub
sudo systemctl start HighwayHub

