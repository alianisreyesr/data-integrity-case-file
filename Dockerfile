FROM python:3.11-slim

WORKDIR /app

# Install curl for the Ollama healthcheck probe
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Seed synthetic data at build time.
# The seed script is idempotent: it checks whether cases already exist
# before inserting, so repeated builds and volume mounts are safe.
RUN mkdir -p data && python data/seed.py

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
