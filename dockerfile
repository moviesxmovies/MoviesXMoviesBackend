FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY . .

RUN adduser --disabled-password --gecos "" django_user && \
    chown -R django_user:django_user /app
USER django_user

EXPOSE 7996

CMD ["sh", "-c", "uv run python manage.py migrate && uv run uvicorn main.asgi:application --host 0.0.0.0 --port 7996 --workers 4"]