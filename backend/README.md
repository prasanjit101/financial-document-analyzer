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
- `REDIS_URL` (optional, for rate limiting)

## Mongo setup

Run Mongo locally via Docker:

```bash
docker run -d --name mongo -p 27017:27017 mongo:7
```

## Auth

- `POST /auth/register` to create a viewer user.
- `POST /auth/login` to obtain JWT using username/password.

## Documents & Analyses

- `POST /analyze` (auth required) uploads a PDF, persists metadata and analysis.
- `GET /documents` (auth required) lists your documents.
- `GET /documents/{id}` (auth required) fetches one.
- `DELETE /documents/{id}` (auth required) deletes one you own.
- `GET /analyses` (auth required) lists analyses filtered by `documentId`.
- `GET /analyses/{id}` (auth required) fetches one.
