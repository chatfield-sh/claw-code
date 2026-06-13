# SHAI Core API image.
# Build context is shai-core/ (the parent) so the image can carry db/ for the
# migration release step:
#   docker build -f api/Dockerfile -t shai-api .
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY api/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY api/app ./app
COPY db ./db

EXPOSE 8000

# Apply schema + seed (idempotent), then serve.
CMD ["sh", "-c", "python -m app.migrate && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
