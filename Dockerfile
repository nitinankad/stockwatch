FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install deps first (layer-cached unless requirements change)
COPY requirements.txt .
COPY backend/requirements.txt backend-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r backend-requirements.txt

COPY . .
