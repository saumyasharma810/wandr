# Wandr

A FastAPI-based travel trip management application with JWT authentication, SQLModel, and SQLite.

## Features

- **Trip Management**: Full CRUD operations for travel trips
- **Authentication**: JWT access + refresh token flow with Argon2 password hashing
- **Rate Limiting**: Brute-force protection on login and refresh endpoints
- **Database**: PostgreSQL with SQLModel and Alembic migrations
- **Testing**: pytest suite with isolated database fixtures
- **Migrations**: Alembic support for schema changes

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/saumyasharma810/wandr.git
   cd wandr
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy and configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```env
   SECRET_KEY=your-long-random-secret-key
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   REFRESH_TOKEN_EXPIRE_DAYS=7
   DATABASE_URL=postgresql://user:password@localhost:5432/wandr
   ```

5. Run migrations:
   ```bash
   alembic upgrade head
   ```

6. Run the application:
   ```bash
   fastapi dev app/main.py
   ```

## API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger UI once the server is running.

## Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create a new user account |
| POST | `/auth/login` | Login and receive access + refresh tokens |
| POST | `/auth/refresh` | Exchange a refresh token for new tokens |
| POST | `/auth/logout` | Invalidate a refresh token |

### Token Flow

1. **Register** → `POST /auth/register` with `{ username, email, password }`
2. **Login** → `POST /auth/login` (form data) → returns `{ access_token, refresh_token, token_type }`
3. **Protected requests** → send `Authorization: Bearer <access_token>` header
4. **Token expired** → server returns `401 { "detail": "Token Expired" }` → call `/auth/refresh`
5. **Refresh** → `POST /auth/refresh` with `{ refresh_token }` → returns new token pair (old refresh token is invalidated)
6. **Logout** → `POST /auth/logout` with `{ refresh_token }` → invalidates the refresh token

Protected routes require `Authorization: Bearer <access_token>`. Use the Swagger UI **Authorize** button after login to test secured endpoints.

## Trip Endpoints

| Method | Endpoint | Description | Auth required |
|---|---|---|---|
| GET | `/trips` | List your trips (pagination supported) | Yes |
| GET | `/trips/{id}` | Get one of your trips by ID | Yes |
| POST | `/trips` | Create a new trip | Yes |
| PATCH | `/trips/{id}` | Update your trip | Yes |
| DELETE | `/trips/{id}` | Delete your trip | Yes |
| GET | `/users/me` | Get current user profile | Yes |

## Testing

```bash
pytest
```

## Project Structure

```
wandr/
├── app/
│   ├── __init__.py
│   ├── main.py        # FastAPI app and trip endpoints
│   ├── auth.py        # Auth routes and JWT logic
│   ├── models.py      # SQLModel table definitions
│   ├── schemas.py     # Pydantic request/response schemas
│   ├── config.py      # Settings loaded from .env
│   └── database.py    # DB engine and session
├── tests/
│   ├── conftest.py    # Pytest fixtures
│   ├── test_models.py # Model and DB tests
│   └── test_trips.py  # API endpoint tests
├── alembic/
│   └── versions/      # Migration scripts
├── alembic.ini
├── requirements.txt
├── pyproject.toml
├── render.yaml
├── .env.example
└── README.md
```

## Database

PostgreSQL via SQLModel and Alembic for schema migrations.

### Setting up PostgreSQL

1. **Create the database** in psql:
   ```sql
   CREATE DATABASE wandr;
   ```

2. **Set the connection URL** in your `.env`:
   ```env
   DATABASE_URL=postgresql://your_user:your_password@localhost:5432/wandr
   ```

3. **Run migrations** to create all tables:
   ```bash
   alembic upgrade head
   ```

4. **Start the app** — it will connect to PostgreSQL automatically:
   ```bash
   fastapi dev app/main.py
   ```

> To generate a new migration after changing models: `alembic revision --autogenerate -m "describe change"`

## Deployment

Configured for Render — see `render.yaml`.
