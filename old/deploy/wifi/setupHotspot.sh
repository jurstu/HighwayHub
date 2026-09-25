set -ex

sudo nmcli device wifi hotspot ssid HighwayHub password itsTheSecret ifname wlan0

nmcli dev wifi show-password

nmcli connection

UUID=$(nmcli -t -f NAME,UUID connection | awk -F: '$1 == "Hotspot" {print $2; exit}')

# Check if we found a UUID
if [[ -z "$UUID" ]]; then
    echo "❌ No connection named 'Hotspot' found."
    exit 1
fi

echo "✅ Found Hotspot UUID: $UUID"

# Modify the connection
sudo nmcli connection modify "$UUID" connection.autoconnect yes connection.autoconnect-priority 100

#sudo nmcli connection modify <hotspot UUID> connection.autoconnect yes connection.autoconnect-priority 100
