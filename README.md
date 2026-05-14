# Wandr

A FastAPI-based travel trip management application with JWT authentication, PostgreSQL, and Docker.

## Features

- **Trip Management**: Full CRUD operations for travel trips (user-scoped)
- **Authentication**: JWT access + refresh token flow with Argon2 password hashing
- **Rate Limiting**: Brute-force protection on login and refresh endpoints
- **Database**: PostgreSQL with SQLModel and Alembic migrations
- **Testing**: pytest suite with isolated in-memory database fixtures
- **Docker**: single `docker compose up` runs everything

---

## Setup — Docker (recommended)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

**1. Clone the repo:**
```bash
git clone https://github.com/saumyasharma810/wandr.git
cd wandr
```

**2. Create your `.env` from the example:**
```bash
cp .env.example .env
```
Open `.env` and set a real `SECRET_KEY` — everything else can stay as the defaults for local dev:
```env
SECRET_KEY=your-long-random-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
DATABASE_URL=postgresql://postgres:postgres@db:5432/wandr
```
> Note: the `DATABASE_URL` host is `db` (the Docker service name), not `localhost`.

**3. Start everything:**
```bash
docker compose up
```
This pulls PostgreSQL, runs migrations automatically, and starts the API server.

**4. Visit the docs:**
```
http://localhost:8000/docs
```

**To stop:** `docker compose down`
**To stop and wipe the database:** `docker compose down -v`

---

## Setup — Local development (without Docker)

Use this when you want hot-reload, to run tests, or to generate migrations.

**1. Clone and create a virtual environment:**
```bash
git clone https://github.com/saumyasharma810/wandr.git
cd wandr
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

**2. Install dependencies:**
```bash
pip install -r requirements-dev.txt
```

**3. Configure environment:**
```bash
cp .env.example .env
```
Edit `.env` with your local PostgreSQL credentials:
```env
SECRET_KEY=your-long-random-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
DATABASE_URL=postgresql://your_user:your_password@localhost:5432/wandr
```

**4. Create the PostgreSQL database:**
```bash
psql postgres -c "CREATE DATABASE wandr;"
```

**5. Run migrations:**
```bash
alembic upgrade head
```

**6. Start the server with hot-reload:**
```bash
fastapi dev app/main.py
```

---

## Adding features — what to update

| What you change | What else to do |
|---|---|
| Add/modify a model | `alembic revision --autogenerate -m "describe"` → commit the new file |
| Add a pip package | Add to `requirements.txt` → `docker compose build` to rebuild |
| Change `.env` | `docker compose down && docker compose up` |

---

## Testing

```bash
# activate venv first
pytest
```

Tests use an isolated in-memory SQLite database — no PostgreSQL needed to run them.

---

## API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger UI.

## Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create a new user account |
| POST | `/auth/login` | Login — returns access + refresh tokens |
| POST | `/auth/refresh` | Exchange refresh token for a new token pair |
| POST | `/auth/logout` | Invalidate a refresh token |

### Token Flow

1. **Register** → `POST /auth/register` with `{ username, email, password }`
2. **Login** → `POST /auth/login` (form data) → returns `{ access_token, refresh_token, token_type }`
3. **Use** → send `Authorization: Bearer <access_token>` on every protected request
4. **Expired** → server returns `401 { "detail": "Token Expired" }` → call `/auth/refresh`
5. **Refresh** → `POST /auth/refresh` with `{ refresh_token }` → new token pair, old one invalidated
6. **Logout** → `POST /auth/logout` with `{ refresh_token }` → invalidates the session

## Trip Endpoints

All trip endpoints require authentication. Trips are user-scoped — you only see your own.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/trips` | List your trips (supports `offset` + `limit`) |
| GET | `/trips/{id}` | Get a trip by ID |
| POST | `/trips` | Create a new trip |
| PATCH | `/trips/{id}` | Update a trip |
| DELETE | `/trips/{id}` | Delete a trip |
| GET | `/users/me` | Get your profile |

## Project Structure

```
wandr/
├── app/
│   ├── main.py            # FastAPI app and trip endpoints
│   ├── auth.py            # Auth routes and JWT logic
│   ├── models.py          # SQLModel table definitions
│   ├── schemas.py         # Pydantic request/response schemas
│   ├── config.py          # Settings loaded from .env
│   └── database.py        # DB engine and session
├── tests/
│   ├── conftest.py        # Pytest fixtures and helpers
│   ├── test_auth.py       # Auth endpoint tests
│   ├── test_trips.py      # Trip endpoint tests
│   └── test_models.py     # Model unit tests
├── alembic/
│   └── versions/          # Migration scripts
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # + pytest and httpx for testing
├── .env.example
└── README.md
```

## Deployment

Configured for Render — see `render.yaml`.
