# Sytac Data Harvester

A real-time data harvester that consumes Server-Sent Events from three video streaming platforms (Sytflix, Sytazon, Sysney) in parallel, and produces an aggregated JSON report.

## Prerequisites

- Python 3.9+
- Docker (to run the video streaming events server)

## Quick start

### 1. Start the streaming server

```bash
# Intel/AMD
docker run -p 8080:8080 sytacdocker/video-stream-server:latest

# Apple Silicon (M1/M2/M3)
docker run -p 8080:8080 sytacdocker/video-stream-server-arm:latest
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the harvester

```bash
python -m harvester.main
```

The program will consume events for up to 20 seconds (or until 3 "Sytac" users are detected), then output the aggregated results to **stdout** and **`output.json`**.

## Running tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

## Project structure

```
sytac-harvester/
├── harvester/
│   ├── __init__.py
│   ├── config.py          # Constants and configuration
│   ├── models.py          # Domain dataclasses
│   ├── parser.py          # SSE + JSON parsing, timezone conversion
│   ├── consumer.py        # Async HTTP stream consumer
│   ├── aggregator.py      # Event aggregation and bonus analytics
│   └── main.py            # Entry point / orchestrator
├── tests/
│   ├── test_parser.py
│   ├── test_aggregator.py
│   └── test_models.py
├── Dockerfile
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Output format

The output is a JSON document with this structure:

```json
{
  "users": [
    {
      "user_id": 42,
      "name": "Elena",
      "surname": "Doe",
      "age": 33,
      "successful_streams": 1,
      "events": [
        {
          "event_type": "stream-started",
          "platform": "Sytflix",
          "show_title": "Test Show",
          "first_cast_member": "Alice Smith",
          "show_id": "s41",
          "event_time_amsterdam": "27-02-2023 04:20:17.111"
        }
      ]
    }
  ],
  "shows_released_2020_or_later": 15,
  "duration_ms": 20034,
  "bonus": {
    "successful_streams_per_user": { "42": 1 },
    "sytflix_started_stream_percentage": 24.5
  }
}
```

