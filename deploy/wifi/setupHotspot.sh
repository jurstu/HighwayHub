set -ex

sudo nmcli device wifi hotspot ssid HighwayHub password itsTheSecret ifname wlan0

nmcli dev wifi show-password

nmcli connection

#sudo nmcli connection modify <hotspot UUID> connection.autoconnect yes connection.autoconnect-priority 100
