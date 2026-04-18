# Wandr

A FastAPI-based travel trip management application.

## Features

- Trip model with user ID, country, duration, vibe, tips, and public status
- CRUD endpoints for managing trips:
  - GET /trips - Retrieve all trips
  - GET /trips/{id} - Retrieve a specific trip by ID
  - POST /trip - Add a new trip
  - PUT /trips/{id} - Update an existing trip
  - DELETE /trips/{id} - Delete a trip

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/saumyasharma810/wandr.git
   cd wandr
   ```

2. Install dependencies (if using pip):
   ```bash
   pip install fastapi pydantic
   ```

3. Run the application:
   ```bash
   fastapi dev main.py
   ```

   Or using the configured entrypoint:
   ```bash
   fastapi run
   ```

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.

## Project Structure

- `main.py`: Main FastAPI application with routes and models
- `trips.py`: Additional trip-related models (if any)
- `pyproject.toml`: Project configuration