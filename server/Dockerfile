FROM python:3.12-slim

WORKDIR /app

# Pillow needs a couple of system libs for font rendering.
# tzdata lets the container honor the TZ env var (else dates render in UTC).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo libfreetype6 fonts-dejavu-core tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8080

# Composition root: core API + Meta-glasses photo watcher.
CMD ["python", "-m", "app.main"]
