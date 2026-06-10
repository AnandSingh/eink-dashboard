FROM python:3.12-slim

WORKDIR /app

# Pillow needs a couple of system libs for font rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo libfreetype6 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8080

# Runs the API + background workers (watcher loop).
CMD ["python", "-m", "app.api"]
