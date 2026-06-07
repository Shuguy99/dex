FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DEX_SKIP_LLM=1
ENV PYTHONPATH=/app

RUN python -m pytest tests/ -v --tb=short || true

CMD ["python", "main.py"]
