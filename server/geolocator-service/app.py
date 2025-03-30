from flask import Flask, jsonify, request
from geopy.geocoders import Nominatim
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Coordinates:
    latitude: float
    longitude: float


app = Flask(__name__)


def get_coordinates_for_location(place: str) -> Optional[Coordinates]:
    geolocator = Nominatim(user_agent="geo_app")
    location = geolocator.geocode(place)

    if location:
        return Coordinates(location.latitude, location.longitude)
    return None


@app.route("/", methods=["GET"])
def api():
    location = request.args.get("location")
    if location:
        coordinates = get_coordinates_for_location(location)
        if coordinates:
            return jsonify(asdict(coordinates))
        else:
            return f"No coordinates found for location '{location}'", 404

    else:
        return "No location given", 400


if __name__ == "__main__":
    app.run(host="0.0.0.0")
