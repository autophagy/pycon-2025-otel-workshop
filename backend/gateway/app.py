import requests
import os
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/", methods=["GET"])
def api():
    location = request.args.get("location")
    if location:
        r = requests.get(
            app.config["GEOLOCATOR_SERVICE"], params={"location": location}
        )

        if r.status_code == 200:
            coordinates = r.json()

            r = requests.get(app.config["ISS_DISTANCE_SERVICE"], params=coordinates)
            if r.status_code == 200:
                return jsonify(r.json())
            else:
                return r.text, r.status_code
        else:
            return r.text, r.status_code
    else:
        return "No location given", 400


if __name__ == "__main__":
    geolocator_service_url = os.getenv("GEOLOCATOR_SERVICE_URL")
    iss_distance_service_url = os.getenv("ISS_DISTANCE_SERVICE_URL")
    if geolocator_service_url and iss_distance_service_url:
        app.config.update(
            GEOLOCATOR_SERVICE=geolocator_service_url,
            ISS_DISTANCE_SERVICE=iss_distance_service_url,
        )
        app.run(host="0.0.0.0")
    else:
        raise RuntimeError("Geolocator/ISS Distance services not defined")
