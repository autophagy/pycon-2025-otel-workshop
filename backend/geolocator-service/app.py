from flask import Flask, jsonify, request
from geopy.geocoders import Nominatim
from dataclasses import dataclass, asdict
from typing import Optional

from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, Resource

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import (
    get_tracer_provider,
    set_tracer_provider,
    get_current_span,
    StatusCode,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from opentelemetry.instrumentation.flask import FlaskInstrumentor


def setup_tracing(resource: Resource):
    """
    Sets up tracing provider that exports spans as soon as they are resolved, and
    assigns it to be the global trace provider.
    """

    span_exporter = OTLPSpanExporter(insecure=True)
    span_processor = SimpleSpanProcessor(span_exporter)
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(span_processor)
    set_tracer_provider(trace_provider)


resource = Resource(
    attributes={
        SERVICE_NAME: "geolocator-service",
        DEPLOYMENT_ENVIRONMENT: "dev",
    }
)

setup_tracing(resource)

tracer = get_tracer_provider().get_tracer(__name__)


@dataclass
class Coordinates:
    latitude: float
    longitude: float


app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)


@tracer.start_as_current_span("getting-coordinates-for-location")
def get_coordinates_for_location(place: str) -> Optional[Coordinates]:
    geolocator = Nominatim(user_agent="Pycon2025OtelWorkshop/1.0")
    location = geolocator.geocode(place)

    if location:
        return Coordinates(location.latitude, location.longitude)
    return None


@app.route("/", methods=["GET"])
def api():
    span = get_current_span()
    location = request.args.get("location")
    if location:
        coordinates = get_coordinates_for_location(location)
        if coordinates:
            return jsonify(asdict(coordinates))
        else:
            span.set_status(StatusCode.ERROR)
            return f"No coordinates found for location '{location}'", 404

    else:
        span.set_status(StatusCode.ERROR)
        return "No location given", 400


if __name__ == "__main__":
    app.run(host="0.0.0.0")
