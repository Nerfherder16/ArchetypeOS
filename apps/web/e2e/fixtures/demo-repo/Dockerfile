# Minimal Dockerfile for the e2e scan fixture. Its presence (with no
# .env.example alongside) makes the scanner surface a deterministic
# DOCKER_WITHOUT_ENV_TEMPLATE risk flag ("...no .env.example/.env.sample
# template found"), which the control-tower spec asserts as the ".env" flag.
FROM python:3.12-slim
WORKDIR /app
COPY example.py /app/example.py
CMD ["python", "example.py"]
