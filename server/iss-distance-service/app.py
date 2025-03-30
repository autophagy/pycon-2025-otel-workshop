import requests
from dataclasses import dataclass, asdict
from flask import Flask, request, jsonify
from geopy.distance import geodesic

ISS_NOW_URL = "http://api.open-notify.org/iss-now.json"

app = Flask(__name__)


@dataclass
class Coordinates:
    latitude: float
    longitude: float


def get_iss_coordinates() -> Coordinates:
    r = requests.get(ISS_NOW_URL)

    if r.status_code == 200:
        position = r.json().get("iss_position")
        if position:
            return Coordinates(float(position.get("latitude")), float(position.get("longitude")))
    return Coordinates(0, 0)


def calculate_distance(location: Coordinates, iss_location: Coordinates) -> float:
    distance = geodesic(
        (location.latitude, location.longitude),
        (iss_location.latitude, iss_location.longitude),
    ).km
    return round(distance, 2)


@app.route("/", methods=["GET"])
def api():
    latitude = request.args.get("latitude")
    longitude = request.args.get("longitude")

    if latitude and longitude:
        iss_location = get_iss_coordinates()
        location = Coordinates(float(latitude), float(longitude))
        distance = calculate_distance(location, iss_location)
        return jsonify({"distance": distance,
                        "location": asdict(iss_location)})
    else:
        return "No latitude/longitude given", 400


if __name__ == "__main__":
    app.run(host="0.0.0.0")
