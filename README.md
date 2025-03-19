#  Instrumenting Python Applications with OpenTelemetry

## Objective

- Instrument an existing service with logs, metrics and traces using OpenTelemetry
- Send OpenTelemetry data to a set of telemetry backends
- Use UIs to explore and make sense of observability data

## Agenda

1. Introduction to Observability and OpenTelemetry
1. Tour of the Application and Tooling
1. Instrument the application
  1. Logging
  1. Metrics
  1. Tracing
1. Tie everything together

## Prerequisites

- Python 3.X
- Docker-compose

## Telemetry Backends

For this workshop, we will use a suite of backend services for telemetry. These are

- [Prometheus](https://prometheus.io/) for metrics.
- [Loki](https://grafana.com/oss/loki/) for logging.
- [Jaeger](https://www.jaegertracing.io/) and [Tempo](https://grafana.com/docs/tempo/latest/) for tracing.

To start these backends using [Docker Compose](https://docs.docker.com/compose/), run the following:

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
