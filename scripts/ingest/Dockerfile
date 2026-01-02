FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gdal-bin \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
        proj-bin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY scripts/ingest/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

ENTRYPOINT ["python", "scripts/ingest/scan_assets.py"]
