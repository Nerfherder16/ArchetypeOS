FROM python:3.12-slim

WORKDIR /app

COPY packages/aos_core /aos_core_pkg
RUN pip install --no-cache-dir /aos_core_pkg

COPY apps/worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/worker/app ./app

CMD ["python", "-m", "app.worker"]
