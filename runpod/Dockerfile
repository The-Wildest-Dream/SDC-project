FROM python:3.13.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY runpod/requirements.txt /app/runpod/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/runpod/requirements.txt

# Build with repository root as context so this uses the project's existing
# inference code and trusted, checked-in model artifact.
COPY price_model.py /app/price_model.py
COPY models/historical_price/model.joblib /app/models/historical_price/model.joblib
COPY runpod/handler.py /app/runpod/handler.py

CMD ["python", "/app/runpod/handler.py"]
