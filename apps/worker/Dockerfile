FROM python:3.12-slim

WORKDIR /app

COPY packages/aos_core /aos_core_pkg
RUN pip install --no-cache-dir /aos_core_pkg

COPY apps/worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# RFC-0010 / AOS-EMBED-002: the real embedding tier (fastembed / ONNX, ~50 MB, no
# torch). Installed unconditionally — it stays dormant unless EMBEDDING_PROVIDER=fastembed.
COPY apps/worker/requirements-embeddings.txt .
RUN pip install --no-cache-dir -r requirements-embeddings.txt

# Optionally pre-download the embedding model so a real offline node runs without
# a first-use fetch. Default false so the compose-smoke build stays fast (no ~90 MB
# model download): build with --build-arg PREDOWNLOAD_EMBEDDING_MODEL=true on an
# offline node. EMBEDDING_MODEL matches config.embedding_model.
ARG PREDOWNLOAD_EMBEDDING_MODEL=false
ARG EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
RUN if [ "$PREDOWNLOAD_EMBEDDING_MODEL" = "true" ]; then \
        python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='$EMBEDDING_MODEL')"; \
    fi

COPY apps/worker/app ./app

CMD ["python", "-m", "app.worker"]
