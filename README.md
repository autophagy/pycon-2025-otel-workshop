#  ![Instrumenting Python Applications with OpenTelemetry](static/Title.png)

## ![Workshop](static/Workshop.png)

### Objective

- Instrument an existing service with logs, metrics and traces using OpenTelemetry
- Send OpenTelemetry data to a set of telemetry backends
- Use UIs to explore and make sense of observability data

### Agenda

1. Introduction to Observability and OpenTelemetry
1. Tour of the Application and Tooling
1. Instrument the application
  1. Logging
  1. Metrics
  1. Tracing
1. Tie everything together

### Prerequisites

- Python 3.X
- Docker-compose

## ![Telemetry Platform](static/TelemetryPlatform.png)

For this workshop, we will use a suite of services to build our telemetry platform. These are

- [Prometheus](https://prometheus.io/) for metrics.
- [Loki](https://grafana.com/oss/loki/) for logging.
- [Jaeger](https://www.jaegertracing.io/) and [Tempo](https://grafana.com/docs/tempo/latest/) for tracing.

To start the telemetry platform using [Docker Compose](https://docs.docker.com/compose/), run the following:

```sh
> docker-compose up -d
```

This will start the above services in the background, you can check on their status by running `docker ps`.

The UIs for these services will then be accessable at:

- Prometheus - <http://localhost:9090>
- Jaeger - <http://localhost:16686>
- Grafana - <http://localhost:3000>

To pause the backends, run:

```sh
> docker-compose stop
```

To remove the backends and their containers, run:

```sh
> docker-compose down
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
> docker-compose -f docker-compose-services.yml up --build
```

To start the services in **watch** mode, so that they are rebuilt and restarted on
code changes, run:

```
sh
> docker-compose -f docker-compose-services.yml watch
```

After either of these, the frontend will be available at <http://localhost:5000>.

To stop the services, run:

```
> docker-compose -f docker-compose-services.yml down
```