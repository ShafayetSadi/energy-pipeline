FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN pip install --no-cache-dir \
    "aiomqtt>=2.3.0" \
    "pyyaml>=6.0.0"

COPY simulator /app

CMD ["python", "mqtt_publisher.py"]
