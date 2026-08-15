FROM python:3.11-slim

# Unbuffered so logs reach `docker logs` immediately instead of sitting in a pipe.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# requirements.txt is generated from uv.lock, so this matches the local venv
# exactly. Regenerate with:
#   uv export --no-dev --no-hashes --format requirements-txt -o requirements.txt
#
# No gcc/libpq-dev here: asyncpg, PyNaCl and cffi all ship manylinux wheels,
# and nothing in this project links against libpq.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Somewhere to keep the LFT sqlite file so it survives a container restart.
RUN mkdir -p /app/data \
    && useradd --create-home --uid 1000 bot \
    && chown -R bot:bot /app
USER bot

# Keep-alive HTTP server for Render; binds $PORT (default 10000).
EXPOSE 10000

CMD ["python", "main.py"]
