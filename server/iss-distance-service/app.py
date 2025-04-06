import requests
from dataclasses import dataclass, asdict
from flask import Flask, request, jsonify
from opentelemetry.sdk.resources import Resource
from geopy.distance import geodesic
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.metrics import (
    get_meter_provider,
    set_meter_provider,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader


# 0. Set up an otel resource for the service
resource=Resource.create(
    {
        "service.name": "iss-distance-service",
    }
)

# 1. Set up the metrics exporter and provider.
exporter = OTLPMetricExporter(insecure=True)
reader = PeriodicExportingMetricReader(exporter)
provider = MeterProvider(resource=resource, metric_readers=[reader])
set_meter_provider(provider)

# 2. Create a meter
meter = get_meter_provider().get_meter("service.meter", "0.1.0")

# 3. Create a counter
incoming_request_counter = meter.create_counter(
    "incoming.requests",
    description="the number of requests made to the service",
)
iss_request_counter = meter.create_counter(
    "iss.requests",
    description="the number of requests made to iss endpoint",
)

ISS_NOW_URL = "http://api.open-notify.org/iss-now.json"

app = Flask(__name__)

@dataclass
class Coordinates:
    latitude: float
    longitude: float


def get_iss_coordinates() -> Coordinates:
    r = requests.get(ISS_NOW_URL)
    # 5. Use the counter for requests to the iss endpoint and add the status code as a field
    iss_request_counter.add(1, {"response.status": r.status_code})

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
    # 4. Use the counter for incoming requests
    incoming_request_counter.add(1)

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
