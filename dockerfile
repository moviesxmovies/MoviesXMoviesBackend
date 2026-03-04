FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    gcc \
    g++ \
    libjpeg-dev \
    zlib1g-dev \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

RUN mkdir -p /app/staticfiles /app/media && \
    adduser --disabled-password --gecos "" django_user && \
    chown -R django_user:django_user /app

USER django_user

EXPOSE 7996
RUN python manage.py collectstatic --noinput

CMD ["sh", "-c", "python manage.py migrate && guvicorn main.wsgi:application --host 0.0.0.0 --port 7996 --workers 4"]