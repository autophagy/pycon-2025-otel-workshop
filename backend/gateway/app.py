import requests
import os
from flask import Flask, request, jsonify

from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, Resource

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import get_tracer_provider, set_tracer_provider, get_current_span, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.semconv.trace import SpanAttributes

from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

def setup_tracing(resource:Resource):
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
        SERVICE_NAME: "gateway",
        DEPLOYMENT_ENVIRONMENT: "dev",
    }
)

setup_tracing(resource)

tracer = get_tracer_provider().get_tracer(__name__)

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

@app.route("/", methods=["GET"])
def api():
    span = get_current_span()
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
                span.set_attribute("error.text", r.text)
                span.set_status(StatusCode.ERROR)
                return r.text, r.status_code
        else:
            span.set_attribute("error.text", r.text)
            span.set_status(StatusCode.ERROR)
            return r.text, r.status_code
    else:
        span.set_status(StatusCode.ERROR)
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
