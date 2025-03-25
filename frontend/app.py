import requests
from flask import Flask, render_template, request
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# gateway_url = "http://localhost:3001?q={place}"
gateway_url = "http://api.open-notify.org/iss-now.json"

app = Flask(__name__)

def get_iss_coordinates():
    r = requests.get(gateway_url)

    if r.status_code == 200:
        return (
            r.json()["iss_position"]["latitude"],
            r.json()["iss_position"]["longitude"],
        )

    return 0, 0

def get_coordinates(place):
    geolocator = Nominatim(user_agent="geo_app")
    location = geolocator.geocode(place)
    
    if location:
        return location.latitude, location.longitude
    return None, None

def calculate_distance(lat, long, issLat, issLong):
    coords_place = (lat, long)
    coords_iss = (issLat, issLong)
    distance = geodesic(coords_iss, coords_place).km
    return round(distance, 2)

@app.route("/", methods=["GET", "POST"])
def homepage():
    lat = long = dist = place = None
    issLat, issLong = get_iss_coordinates()

    if request.method == 'POST':
        place = request.form['place']

        issLat, issLong = get_iss_coordinates()
        lat, long = get_coordinates(place)
        dist = calculate_distance(lat, long, issLat, issLong)
    return (
        render_template("index.html", latitude=issLat, longitude=issLong, distance=dist, place=place),
        200,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0")
