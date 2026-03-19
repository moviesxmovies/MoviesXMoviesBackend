# MoviesXMovies Backend

A Django REST API backend for the MoviesXMovies platform — a social movie tracking application where users can discover movies, write reviews, rate films, manage watchlists, and follow other users.

## Features

- 🎬 **Movie catalog** with multilingual support (EN, ES, FR, DE) and cover images
- ⭐ **Ratings & Reviews** with comments, replies, and reactions
- 🤖 **AI-powered recommendations** via Alternating Least Squares (ALS) collaborative filtering
- 👥 **Social features** — follow users, see friends' ratings, get suggested users
- 📋 **Movie lists** for organizing and sharing collections
- 🔐 **Authentication** via JWT and Google OAuth
- 📧 **Email verification** and password recovery
- 🏆 **Awards** and **platforms** tracking per movie
- 📊 **Prometheus metrics** and **SonarQube** code quality integration
- 🌍 **i18n** support with locale files

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 6 + Django REST Framework |
| Database | PostgreSQL (SQLite for dev) |
| Cache / Queue | Redis + RQ + RQ Scheduler |
| Auth | JWT (SimpleJWT) + Google OAuth (dj-rest-auth + allauth) |
| Recommendations | Implicit (ALS) |
| API Docs | drf-spectacular (OpenAPI) |
| Server | Gunicorn |
| Containerization | Docker |
| Package Manager | uv |
| Python | 3.14+ |

## Project Structure

```
.
├── awards/          # Award model and API
├── genres/          # Genre model and API
├── movies/          # Movie catalog, translations, recommendations
├── movielists/      # User movie lists
├── persons/         # Directors and actors
├── platforms/       # Streaming platforms
├── ratings/         # Movie ratings (1–5)
├── reviews/         # Reviews with comments, replies, and reactions
├── shared/          # Base models, decorators, middleware, utilities
├── users/           # User accounts, auth, following
├── tests/           # Global test suite
└── main/            # Django settings, URL routing, WSGI/ASGI
```

## Getting Started

### Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) package manager
- PostgreSQL (or SQLite for local dev)
- Redis

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-org/MoviesXMoviesBackend.git
   cd MoviesXMoviesBackend
   ```

2. **Install dependencies**

   ```bash
   uv sync
   ```

3. **Configure environment variables**

   Copy the example env file and fill in your values:

   ```bash
   cp example.env .env
   ```

   | Variable | Description |
   |---|---|
   | `SECRET_KEY` | Django secret key |
   | `DEBUG` | `True` for development |
   | `DB_ENGINE` | e.g. `django.db.backends.postgresql` |
   | `DB_NAME` | Database name (or SQLite file path) |
   | `TMDB_API_KEY` | API key from [The Movie Database](https://www.themoviedb.org/) |
   | `EMAIL_HOST` | SMTP host (default: Brevo) |
   | `EMAIL_PORT` | SMTP port |
   | `EMAIL_HOST_USER` | SMTP username |
   | `EMAIL_HOST_PASSWORD` | SMTP password |
   | `DEFAULT_FROM_EMAIL` | Sender email address |

4. **Apply migrations**

   ```bash
   python manage.py migrate
   ```

5. **Run the development server**

   ```bash
   python manage.py runserver
   ```

6. **(Optional) Start the RQ worker** for background tasks (e.g. retraining the recommendation model)

   ```bash
   python manage.py rqworker
   ```

### Docker

Build and run with Docker:

```bash
docker build -t moviesxmovies-backend .
docker run -p 7996:7996 --env-file .env moviesxmovies-backend
```

The app is served by Gunicorn on port **7996** with 4 workers.

The official image is published to Docker Hub:

```bash
docker pull moviesxmovies/backend:latest
```

## API Overview

API documentation is auto-generated via **drf-spectacular** and available at `/api/schema/` once the server is running.

### Main Endpoint Groups

| Prefix | Description |
|---|---|
| `auth/` | Login, signup, token refresh, password recovery |
| `oauth/google/` | Google OAuth login |
| `users/` | User profile, follow/unfollow, suggested users |
| `movies/` | Movie list, details, recommendations, ratings, reviews |
| `reviews/` | Review CRUD, comments, replies, reactions |
| `movielists/` | Create and manage movie lists |
| `persons/` | Directors and actors |
| `platforms/` | Streaming platform info |
| `awards/` | Award listings |

Authentication uses **JWT Bearer tokens**. Include the token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

## Recommendation Engine

Movie recommendations are powered by **collaborative filtering** using the [Implicit](https://github.com/benfred/implicit) library's ALS model. The model is trained on user ratings, serialized with `pickle`, and cached in Redis.

The model retrains asynchronously via an RQ background job (`retrain_professional_model`). Recommendations are fetched at `GET /movies/` for authenticated users.

## Running Tests

```bash
pytest
```

To run with coverage:

```bash
pytest --cov
```

Test configuration is in `pytest.ini`. The test suite uses `pytest-django`, `factory-boy`, and `pytest-rich`.

## CI/CD

GitHub Actions workflows handle the full pipeline:

| Workflow | Trigger | Action |
|---|---|---|
| `Checks` | Push / PR | Runs tests and linting |
| `SonarQube` | Push / PR | Code quality analysis |
| `Build Docker Image` | After Checks pass on `main` | Builds and pushes to Docker Hub |
| `Deploy` | After Docker build on `main` | SSH deploy via `docker compose up` |
| `Docs` | On release | Generates API documentation |
| `Changelog` | On release | Generates changelog |

## Internationalization

The API supports content in **English**, **Spanish (es)**, **French (fr)**, and **German (de)**. Movies have a `MovieTranslation` model for localized titles, synopses, and cover images. Locale files are located in each app's `locale/` directory.

## License
[License](license.txt)
