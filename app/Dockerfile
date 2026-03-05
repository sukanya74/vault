FROM python:3.12-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime

RUN groupadd -r app && useradd -r -g app app
WORKDIR /app
COPY --from=builder /install /usr/local
COPY main.py db.py ./
RUN mkdir -p /run/secrets && chown app:app /run/secrets

USER app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]

