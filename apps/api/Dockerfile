FROM python:3.12-slim

WORKDIR /app

# Build context is the repo root so the shared core package can be installed.
COPY packages/aos_core /aos_core_pkg
RUN pip install --no-cache-dir /aos_core_pkg

COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api/app ./app
COPY apps/api/alembic.ini .
COPY apps/api/alembic ./alembic
COPY apps/api/docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
