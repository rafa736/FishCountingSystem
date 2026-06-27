FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

ENV YOLO_CONFIG_DIR=/tmp/Ultralytics

CMD ["gunicorn", "app:app", "--bind=0.0.0.0:8080", "--timeout=180", "--preload", "--workers=1", "--threads=2"]