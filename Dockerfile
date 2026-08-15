FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
  gcc \
  libpq-dev \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Nothing listens on a port: this is a gateway client, not a web service.
CMD ["python", "main.py"]
