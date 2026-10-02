sudo cp highwayhub.service /etc/systemd/system/highwayhub.service
sudo systemctl daemon-reload
sudo systemctl enable --now highwayhub.service
sudo systemctl restart highwayhub.service


