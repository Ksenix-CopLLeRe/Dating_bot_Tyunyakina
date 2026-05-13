# Performance and load testing

The backend exposes lightweight endpoints that are useful for smoke and load
checks:

- `GET /health`
- `POST /users/register`
- `GET /metrics`

Run the local stack first:

```bash
docker compose up --build
```

Then run the JMeter plan from a machine with Apache JMeter installed:

```bash
jmeter -n -t docs/stage4-load-test.jmx -Jhost=localhost -Jport=8000 -Jthreads=25 -Jloops=20 -l load-results.jtl
```

The plan uses configurable properties, so the same file can target a server:

```bash
jmeter -n -t docs/stage4-load-test.jmx -Jhost=example.com -Jport=80 -Jthreads=50 -Jloops=100 -l load-results.jtl
```
