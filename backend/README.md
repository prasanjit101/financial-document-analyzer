# Backend

- Redis for rate limiting, caching
- MongoDB for storing documents, analysis results, and history
- FastAPI for the API
- CrewAI for the agents
- JWT based authentication with role based access control (Admin, Viewer). Use authlib for the authentication.
- pydantic for strict type checking

## Environment

Configure via env or `.env` (see `backend/config.py` for defaults):

- `MONGODB_URI` (default: `mongodb://localhost:27017`)
- `MONGODB_DB_NAME` (default: `financial_analyzer`)
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM` (default: `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES` (default: `60`)
- `REDIS_URL` (required for background jobs and caching; optional for just rate limiting)
  - `CACHE_TTL_DEFAULT_SECONDS` (default 60)
  - `CACHE_TTL_LONG_SECONDS` (default 300)

## Mongo setup

Run Mongo locally via Docker:

```bash
docker run -d --name mongo -p 27017:27017 mongo:7
```

## Auth

- `POST /auth/register` to create a viewer user.
- `POST /auth/login` to obtain JWT using username/password.

## Documents & Analyses

- `POST /v1/documents/analyze` (auth required) uploads a PDF and enqueues background analysis; returns `jobId`.
- `GET /v1/documents` (auth required) lists your documents.
- `GET /v1/documents/{id}` (auth required) fetches one.
- `DELETE /v1/documents/{id}` (auth required) deletes one you own.
- `GET /v1/analyses` (auth required) lists analyses filtered by `documentId`.
- `GET /v1/analyses/{id}` (auth required) fetches one.
 - `GET /v1/documents/jobs/{jobId}` (auth required) returns job status and `analysis_id` on completion.

## Background worker

Start Redis locally if needed:

```bash
docker run -d --name redis -p 6379:6379 redis:7
```

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
  uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Step 2: Generate the OpenAPI schema
```bash
  curl -s http://localhost:8000/openapi.json -o backend/openapi.json
```