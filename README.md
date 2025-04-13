#  ![Instrumenting Python Applications with OpenTelemetry](static/Title.png)

## ![Workshop](static/Workshop.png)

### Objective

- Instrument an existing service with logs, metrics and traces using OpenTelemetry
- Send OpenTelemetry data to a set of telemetry backends
- Use UIs to explore and make sense of observability data

### Agenda

1. Introduction to Observability and OpenTelemetry
2. Tour of the Application and Tooling
3. Instrument a service in the application
    1. [Logging](#section-1-logging)
    1. [Metrics](#section-2-metrics)
    1. [Tracing](#section-3-tracing)
4. [Tie everything together](#section-4-tying-it-all-together)

### Useful Resources

- [OpenTelemetry documentation](https://opentelemetry.io/docs/)
    - [Concepts](https://opentelemetry.io/docs/concepts/)
    - [Python](https://opentelemetry.io/docs/languages/python/)
- [OpenTelemetry Python SDK](https://github.com/open-telemetry/opentelemetry-python)
    - [Examples](https://github.com/open-telemetry/opentelemetry-python/tree/main/docs/examples)
    - [API Reference](https://opentelemetry-python.readthedocs.io/en/latest/)
- OpenTelemetry Autoinstrumentation
    - [Flask](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/flask/flask.html)
    - [Requests](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/requests/requests.html)

### Prerequisites

All you need is `docker` installed since we'll be using this to run and orchestrate the services and infrastructure.
You don't even need to have a particular version of Python installed on your machine.

## ![Telemetry Platform](static/TelemetryPlatform.png)

For this workshop, we will use a suite of services to build our telemetry platform:

- [Prometheus](https://prometheus.io/) for metrics.
- [Loki](https://grafana.com/oss/loki/) for logging.
- [Tempo](https://grafana.com/docs/tempo/latest/) for tracing.

To start the telemetry platform using [Docker Compose](https://docs.docker.com/compose/), run the following:

```sh
> docker compose up -d
```

This will start the above services in the background, you can check on their status by running `docker ps`.

The UIs for these services will then be accessable at:

- Prometheus - <http://localhost:9090>
- Grafana - <http://localhost:3000>

To pause the backends, run:

```sh
> docker compose stop
```

To remove the backends and their containers, run:

```sh
> docker compose down
```

## ![Backend Services](static/BackendServices.png)

![Schema Diagram of backend services](static/BackendSchema.png)

This workshop revolves around instrumenting an example microservice application. This application
allows a user to determine the distance of a location from the current location of the
International Space Station. It is composed of the following services:

- `frontend` - The frontend service that calls out to the `gateway`.
- `backend/gateway` - The gateway service that handles requests from the `frontend`.
- `backend/geolocator-service` - A service that takes in a location string, and attempts
  to return the coordinates for that location.
- `backend/iss-distance-service` - A service that takes in a coordinate, gets the current
  location of the International Space Station, and returns the distance of the ISS from the
  given coordinates.

To build and start the services:

```sh
> docker compose -f docker-compose-services.yml up --build
```

To start the services in **watch** mode, so that they are rebuilt and restarted on
code changes, run:

```sh
> docker compose -f docker-compose-services.yml watch
```

After either of these, the frontend will be available at <http://localhost:5000>.

To stop the services, run:

```sh
> docker compose -f docker-compose-services.yml down
```

---

## ![Workshop Material](static/WorkshopMaterial.png)

Sections 1-3 will involve instrumenting just one of the services, the `iss-distance-service`. In Section 4
we'll tie everything together and instrument across all four services.

### Section 0: Create an OpenTelemetry Resource

The first thing we'll need to do is put the setup in place to support instrumenting with OpenTelemetry.

In an editor, open up `backend/iss-distance-service/app.py`.

Instrumenting a service starts with creating an OTel `Resource`. A `Resource` is a representation of the entity producing telemetry, i.e. a representation of the service which produces the metrics, traces and/or logs, which in this case is the `iss-distance-service`.  

To define a resource for our service, begin by importing the following:

```python
from opentelemetry.sdk.resources import (
    DEPLOYMENT_ENVIRONMENT,
    SERVICE_NAME,
    Resource,
)
```
Then, towards the top of the file, add the following resource and set the values:

```python
resource = Resource(
    attributes={
        SERVICE_NAME: "iss-distance-service",
        DEPLOYMENT_ENVIRONMENT: "dev",
    }
)
```

This creates a resource, and provides further context about it using `attributes`. These attributes that we set on the resource are applicable to the service as a whole and will be relevant
to all telemetry exported e.g., we can set things such as the service name, version, environment. 

We will later use this resource when initialising metrics, logging and tracing.

### Section 1: Metrics

#### i. Setup metrics

Before we can begin creating and exporting metrics, we need to do some setup.

Again, open up `backend/iss-distance-service/app.py`.

Add the following to the list of imports (each of these imports will be explained when we use them):

```python
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.metrics import (
    get_meter_provider,
    set_meter_provider,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
```

First we use these imports to set up a metrics `exporter` and `provider`. Create a `setup_metrics` method which accepts one argument of type `resource`:

```python
def setup_metrics(resource: Resource):
    """
    Sets up a metrics reader that exports every 1 second, and assigns it to be the
    global meter provider.
    """

    metric_exporter = OTLPMetricExporter(insecure=True)
    metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=1000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    set_meter_provider(meter_provider)
```

This sets up the OTLP exporter to send metrics over OTLP to a backend (in our case the OpenTelemetry Collector). Setting `insecure=True` means it will send data over HTTP rather than HTTPS. The `MetricReader` exports metrics periodically. The `MeterProvider` manages the metrics meters and receives the resource that was created in Section 0. Finally we set the meter provider as the global provider, which allows the rest of our service to make use of it. 

Next, outside of any methods, we call the method we've created above to setup metrics, and then create a `meter` which will be used to generate metrics:

```python
setup_metrics(resource)

meter = get_meter_provider().get_meter(__name__)
```

#### ii. Create metrics

There are several different types of metrics that can be created, such as counters, histograms and gauges. In this section, we will focus on creating a counter, but we encourage you to explore all metric types. 

Directly below where you have defined the `meter`, create the following `counters` which will be used to count requests; one counter to count incoming requests received by the service, and the other to count outgoing requests to the ISS endpoint.

```python
incoming_request_counter = meter.create_counter(
    "incoming.requests",
    description="the number of requests made to the service",
)
iss_request_counter = meter.create_counter(
    "iss.requests",
    description="the number of requests made to iss endpoint",
)
```

Then use the counters to generate metrics by adding the following,

In the `api()` method:


```python
incoming_request_counter.add(1)
```

In the `get_iss_coordinates()` method, after the request is made we can increment the `iss_request_counter` and add the response status code as an attribute.
This will allow us to distiguish between responses which return successfully and error responses. When considering attributes to add, we need to keep their cardinality in mind, and should avoid high cardinality attributes (i.e. highly unique attributes such as UUIDs), we can result in costly metrics.

```python
iss_request_counter.add(1, {"response.status": r.status_code})
```


#### iii. Explore metrics with Grafana and Prometheus

Now that the metrics are being exported, we can check that they're being ingested into our telemetry
platform. Let's first check Prometheus. If you go to [Prometheus](http://localhost:9090/query), you
should see a page for querying metrics. Let's try with one of the metrics we added, `iss.requests`.
Note that Prometheus transforms our metric names, replacing `.` and adding `total`, so that the metric is now called
`iss_requests_total`. If you begin to type it into the Prometheus query bar, the metric should autocomplete:

![Querying Prometheus for iss_requests_total](static/metrics/metrics1.png).

If you select `iss_requests_total` and click `Execute`, you should now be able to see your metric:

![Result of querying for iss_requests_total](static/metrics/metrics2.png)

Make a few more requests, you should see the counter increase!

We can also query our metrics in Grafana, using Prometheus as a data source. First, open the
[Explore section in Grafana](http://localhost:3000/explore). From there, select "Prometheus"
as the data source:

![Selecting Prometheus as a data source in Grafana](static/metrics/metrics3.png)

Selecting `iss_requests_total` and running the query will now show your metric.

![Result of querying iss_requests_total in Grafana](static/metrics/metrics4.png)

### Section 2: Logging

#### i. Set up logging

Again, some setup is required before we can create logs. 

Open up `backend/iss-distance-service/app.py` and add the following to the list of imports:

```python
import logging

from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
```

Then, we'll then use these imports to set up the log `provider` and `exporter`. Create a `setup_logging` method, which accepts two arguments the `Resource` and a `Logger`, then add the following:

```python
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

```

This is quite a lot of setup and can seem a bit complicated. To deconstruct line by line what is happening:

```python
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)
```

This creates a `LoggerProvider`, and registers it so the logger provider can be used.


```python
    exporter = OTLPLogExporter(insecure=True)
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    logger_provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))

```

This sets up the OTLP exporter to send logs over OTLP. It then sets up a logging handler to send logs in OTLP format to a destination. We then register a `LogRecordProcessor` on the provider, in this case we use a `SimpleLogRecordProcessor`, which exports logs as soon as they are emitted.

```python
    logger.addHandler(handler)
    logger.level = logging.DEBUG
```

This attaches the handler to the logger and sets the log level to `DEBUG`.

Finally, we can call the `setup_logging` method we've created above:

```python
LOGGER = logging.getLogger("iss-distance-service")
LOGGER.level = logging.DEBUG

setup_logging(resource, LOGGER)
```

#### ii. Create logs

Add logs to the following points in the code to record particular events:

1. When the application is started: `otel_logger.info("started application")`
2. When no latitude or longitude is provided in the request: `otel_logger.warning("Missing latitude/longitude in request")`
3. When an incoming request is received: `otel_logger.info("received request from IP address: %s", request.remote_addr)`
4. When a non-200 response is returned from the ISS endpoint: `otel_logger.error("request to iss endpoint returned a non-200 response")`

#### iii. Explore logs with Grafana and Loki

Now that we are exporting logs, let's check they are being ingested. Again, open [Explore section in Grafana](http://localhost:3000/explore) and select "Loki" as the data source:

![Selecting Loki as Data source in Grafana](static/logs/logs1.png)

We should create a query for searching our logs. For now, let's query the `service_name`, which will
be `iss-distance-service`. If you execute the query, you should see a graph of your logs:

![Result of executing log search on Grafana](static/logs/logs2.png)

If you scroll down, you'll see individual log lines. These log lines can be expanded, and you
can see various attributes about the logs in question:

![Detail of logs](static/logs/logs3.png)

### Section 3: Tracing

#### i. Set up tracing

Like in the previous sections, we'll need to do some setup, before we can create traces.

Again, open up `backend/iss-distance-service/app.py`, and add the following to the list of imports:

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
```

Then, we'll then use these imports to set up the tracing `exporter` and `provider`. Create a `setup_tracing` method which accepts one argument of type, `Resource`, like so:

```python
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
```

This is a lot of new additions in just a few short lines! Let's pause to take a look at what do each of these does: 

- `OTLPSpanExporter` - this is a span exporter. It exports spans to the OpenTelemetry Collector using the OpenTelemetry Protocol (OTLP).
- `TracerProvider` - the provider manages and provides a `tracer` instance. This is used to create spans for distributed tracing.
- `SimpleSpanProcessor` - the span processor exports spans to the `OTLPSpanExporter`. It exports them immediately as they're generated. We use this form of `Processor` for simplicity, but in production applications, you would typically use a `BatchSpanProcessor`.

Next, outside of any methods, we call the method we've created above to setup tracing, and then create a `tracer` which will be used to create spans:

```python
setup_tracing(resource)

tracer = trace.get_tracer_provider().get_tracer(__name__)
```

#### ii. Create spans

Now that we have the setup in place, we can begin capturing useful information.

On the `api` function, we can create the first `span`.

A `trace` represents a journey through the application. It provides a wide view of the journey taken through the code and services. It is comprised of spans.
A `span` represents a single event that occurs as part of journey through the application e.g a span can represent a HTTP request to other microservices or 3rd parties, database queries. Together, spans build traces.

We would like to know when a request is made to the `iss-distance-service`, and how long the request takes.

There are two ways to capture an OpenTelemtry span i. using a method decorator or ii. using `with`. In this example we will use both.

Add the following `with` block to the `api` method, giving the span a suitable name e.g. `"calculating-api-distance"`:

```python
def api():
    with tracer.start_as_current_span("<PLACEHOLDER-SPAN-NAME>") as span:
      ...
```

We would also like to know when a request is made to the `iss_now` API. To know this, we will create a span when this is called. Add the following decorator to the `get_iss_coordinates` method, giving the span a suitable name e.g. `getting-iss-coordinates`, in order to create a `nested span`:

```python
@tracer.start_as_current_span("<PLACEHOLDER-SPAN-NAME>")
def get_iss_coordinates() -> Coordinates:
```

#### iii. Add span attributes

Attributes can be used to add additional metadata information to a span. This information can then be used
when exploring traces and allows you to do things such as grouping or filtering.

If the status code from the request to get the ISS coordinates is successful, we
can set a `span attribute` to capture the coordinates returned:

```python
if r.status_code == 200:
    ...

    span = trace.get_current_span()
    if position:
        coordinates = Coordinates(float(position.get("latitude")), float(position.get("longitude")))
        span.set_attribute("iss.position", str(coordinates))
        return coordinates
```

Because there are some forms of data that are typically useful to capture, there
are `Semantic Attributes` which allow the attributes to be defined in a consistent way. We will use semantic attributes to capture the request method, status and url:

Import the following:
```python
from opentelemetry.semconv.trace import SpanAttributes
```

Add the following after the request is made:

```python
current_span.set_attribute(SpanAttributes.HTTP_METHOD, "GET")
current_span.set_attribute(SpanAttributes.HTTP_STATUS, r.status_code)
current_span.set_attribute(SpanAttributes.HTTP_URL, iss_now_url)
```

Finally, we can handle error cases by setting a span status:

```python

if latitude and longitude:
    ...
    return ...

else:
    span.set_status(trace.StatusCode.ERROR)
    return ...

```

#### iv. Explore traces with Grafana and Tempo

Now that we are exporting traces, let's check they are being ingested. Again, open [Explore section in Grafana](http://localhost:3000/explore) and select "Tempo" as the data source:

![Selecting Tempo as Data source in Grafana](static/traces/traces1.png)

Let's create a basic `Search` query, filtering on the service name `iss-distance-service`. You should
see the traces being exported from your service.

![Result of querying Grafana for traces](static/traces/traces2.png)

If you open a trace ID from the result in a new tab, you'll be able to see some detail about the trace:

![Detailed view of a trace](static/traces/traces3.png)

You can see that the trace is made up of spans. You can expand one of the spans to see the extra
attributes you assigned to it:

![Detailed view of a span](static/traces/traces4.png)

### Section 4: Tying it all together

#### Propagating traces between services

#### iv. Explore propagated traces with Grafana

Let's head back to the [Explore section in Grafana](http://localhost:3000/explore) again,
and create a `Search` query from the Tempo data source. You should see that the service
associated with the span is no longer `iss-distance-service` but `gateway` - this is
the service that began the trace.

![Searching for multi-service spans](static/prop/prop1.png)

Opening the trace in a new tab will give you more detail:

![Detailed view of a multi-service trace](static/prop/prop2.png)

You can now see how the trace is composed of multiple spans from *different services*, colour
coded. We can now see the whole path a request makes through our system, and how long it spends
in each span. We can see from detail above that our request spent most of its time in getting
the ISS coordinates, with a smaller amount of time spent resolving the coordinates of a given
location.

### Wrap-Up


