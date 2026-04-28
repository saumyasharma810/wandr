# Wandr

A FastAPI-based travel trip management application with SQLModel and SQLite database integration.

## Features

- **Trip Management**: Full CRUD operations for travel trips
- **Database Integration**: SQLite database with SQLModel (SQLAlchemy + Pydantic)
- **API Endpoints**:
  - GET /trips - Retrieve all trips (with pagination)
  - GET /trips/{id} - Retrieve a specific trip by ID
  - POST /trips - Create a new trip
  - PATCH /trips/{id} - Update an existing trip
  - DELETE /trips/{id} - Delete a trip
- **Data Models**: TripBase, Trip, TripCreate, TripPublic, TripUpdate with proper validation
- **Authentication**: JWT-based user registration and login with OAuth2 Bearer tokens
- **Testing**: Comprehensive pytest suite with isolated database tests
- **Migrations**: Alembic support for database schema changes

## Setup

1. Copy environment example:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill values:
   ```env
   SECRET_KEY=your-secret-key
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

3. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

1. Clone the repository:
   ```bash
   git clone https://github.com/saumyasharma810/wandr.git
   cd wandr
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

   Or using FastAPI CLI:
   ```bash
   fastapi dev app/main.py
   ```

## Testing

Run the test suite:
```bash
pytest
```

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.

## Authentication

- `POST /auth/register`: register a new user
- `POST /auth/login`: obtain a JWT bearer token
- Protected routes require the header `Authorization: Bearer <token>`
- Use the Swagger UI `Authorize` button after login to call secured endpoints

## Project Structure

```
wandr/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application with endpoints
│   ├── models.py        # SQLModel data models (Trip, TripCreate, etc.)
│   └── database.py      # Database engine and session management
├── tests/
│   ├── conftest.py      # Pytest fixtures and configuration
│   ├── test_models.py   # Tests for models and database operations
│   └── test_trips.py    # API endpoint tests
├── alembic/
│   └── versions/        # Database migration scripts
├── alembic.ini          # Alembic configuration
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Project configuration
├── render.yaml          # Render deployment configuration
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## Database

The application uses SQLite with SQLModel for type-safe database operations. Database tables are created automatically on startup. For production deployments, consider using a more robust database like PostgreSQL.

## Deployment

This project is configured for deployment on Render. See `render.yaml` for deployment settings.