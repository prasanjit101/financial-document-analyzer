# Backend

- Redis for rate limiting, caching
- MongoDB for storing documents, analysis results, and history
- FastAPI for the API
- CrewAI for the agents
- JWT based authentication with role based access control (Admin, Viewer). Use authlib for the authentication.
- pydantic for strict type checking

## Mongo setup

Run Mongo locally via Docker:

```bash
docker run -d --name mongo -p 27017:27017 mongo:7
```

## Background worker

Start Redis locally if needed

Run the worker in a separate process:

```bash
python -m backend.worker_pdf
```

The API requires the worker to process analysis jobs. If Redis is unreachable, the analyze endpoint returns 503.

## Caching

The API caches frequently accessed responses in Redis:

- Documents list/detail, Analyses list/detail

Cache invalidation occurs on document deletion; otherwise TTL-based freshness applies.

## OpenAPI JSON generation for the API documentation
Step 1: Run the app
```bash
uv run main.py
```

Step 2: Generate the OpenAPI schema
```bash
  curl -s http://localhost:8000/openapi.json -o backend/openapi.json
```