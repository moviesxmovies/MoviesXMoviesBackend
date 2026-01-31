FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml . 
RUN pip install --no-cache-dir . uvicorn[standard]

COPY . .

RUN adduser --disabled-password --gecos "" django_user
USER django_user

EXPOSE 7996

CMD ["uvicorn", "main.asgi:application", "--host", "0.0.0.0", "--port", "7996", "--workers", "4"]