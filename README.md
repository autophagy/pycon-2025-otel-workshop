#  Instrumenting Python Applications with OpenTelemetry

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
