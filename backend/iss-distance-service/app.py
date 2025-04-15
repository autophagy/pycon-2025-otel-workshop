import requests
import logging
from dataclasses import dataclass, asdict
from flask import Flask, request, jsonify
from geopy.distance import geodesic

from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, Resource

from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import get_tracer_provider, set_tracer_provider, get_current_span, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.semconv.trace import SpanAttributes

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor

from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

LOGGER = logging.getLogger("iss-distance-service")

def setup_metrics(resource: Resource):
    """
    Sets up a metrics reader that exports every 1 second, and assigns it to be the
    global meter provider.
    """

    # 1. Set up the metrics and tracing exporter and provider.
    metric_exporter = OTLPMetricExporter(insecure=True)
    metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=1000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    set_meter_provider(meter_provider)

def setup_logging(resource: Resource, logger: logging.Logger):
    """
    Sets up a logging provider that exports logs in batches, and attaches the OTLP handler
    to the given logger.
    """

    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)

    # 2. b. Set up logging exporter and handler
    exporter = OTLPLogExporter(insecure=True)
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    logger_provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))

    logger.addHandler(handler)
    logger.level = logging.DEBUG


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

# 0. Set up an otel resource for the service
resource = Resource(
    attributes={
        SERVICE_NAME: "iss-distance-service",
        DEPLOYMENT_ENVIRONMENT: "dev",
    }
)

# 1. Setup providers
setup_metrics(resource)
setup_logging(resource, LOGGER)
setup_tracing(resource)

# 2. Create a meter and tracer
meter = get_meter_provider().get_meter(__name__)
tracer = get_tracer_provider().get_tracer(__name__)

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
FlaskInstrumentor().instrument_app(app)

@dataclass
class Coordinates:
    latitude: float
    longitude: float


@tracer.start_as_current_span("getting-iss-coordinates")
def get_iss_coordinates() -> Coordinates:
        r = requests.get(ISS_NOW_URL)
        # 5. Use the counter for requests to the iss endpoint and add the status code as a field
        iss_request_counter.add(1, {"response.status": r.status_code})
        span = get_current_span()
        span.set_attribute(SpanAttributes.HTTP_METHOD, "GET")
        span.set_attribute(SpanAttributes.HTTP_STATUS_CODE, r.status_code)
        span.set_attribute(SpanAttributes.HTTP_URL, ISS_NOW_URL)

        if r.status_code == 200:
            position = r.json().get("iss_position")
            if position:
                coordinates = Coordinates(float(position.get("latitude")), float(position.get("longitude")))
                span.set_attribute("iss.position", str(coordinates))
                return coordinates

        span.set_status(StatusCode.ERROR)
        # 2.d add logging when we don't receive a 200 from the ISS endpoint
        LOGGER.error("request to iss endpoint returned a non-200 response")
        return Coordinates(0, 0)


def calculate_distance(location: Coordinates, iss_location: Coordinates) -> float:
    distance = geodesic(
        (location.latitude, location.longitude),
        (iss_location.latitude, iss_location.longitude),
    ).km
    return round(distance, 2)

@app.route("/", methods=["GET"])
def api():
    with tracer.start_as_current_span("calculating-iss-distance") as span:
        # 4. Use the counter for incoming requests
        incoming_request_counter.add(1)
        # 2.e add logging when request received
        LOGGER.info("received request from IP address: %s", request.remote_addr)


        latitude = request.args.get("latitude")
        longitude = request.args.get("longitude")

        if latitude and longitude:
            iss_location = get_iss_coordinates()
            location = Coordinates(float(latitude), float(longitude))
            distance = calculate_distance(location, iss_location)
            return jsonify({"distance": distance,
                            "location": asdict(iss_location)})
        else:
            span.set_status(StatusCode.ERROR)
            # 2.d add logging if no lat/log provided in request
            LOGGER.warning("Missing latitude/longitude in request")
            return f"No latitude/longitude given", 400


if __name__ == "__main__":
    # 2.e add logging on application start
    LOGGER.info("started application")
    app.run(host="0.0.0.0")
