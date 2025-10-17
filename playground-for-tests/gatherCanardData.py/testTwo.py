import requests

# start and end coords (lon, lat)
start = (18.6466, 54.3520)  # Gdańsk
end = (19.0399, 50.2649)    # Katowice

url = f"http://router.project-osrm.org/route/v1/driving/{start[0]},{start[1]};{end[0]},{end[1]}?overview=full&geometries=geojson"
r = requests.get(url)
data = r.json()

# Extract road geometry (list of coordinates)
coords = data["routes"][0]["geometry"]["coordinates"]

print("Number of intermediate points:", len(coords))
import json
print("First 5 points:", json.dumps(coords, indent = 4))