import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def homepage():
    lat = long = dist = location = None

    if request.method == 'POST':
        location = request.form['location']

        r = requests.get(app.config["GATEWAY_URL"], params={"location": location})
        j = r.json()
        dist = j.get("distance")
        lat = j.get("location", {}).get("latitude")
        long = j.get("location", {}).get("longitude")
    return (
        render_template("index.html", latitude=lat, longitude=long, distance=dist, location=location),
        200,
    )


if __name__ == "__main__":
    gateway_url = os.getenv("GATEWAY_URL")
    if gateway_url:
        app.config.update(
            GATEWAY_URL=gateway_url,
        )
        app.run(host="0.0.0.0")
    else:
        raise RuntimeError("GATEWAY_URL not defined")
