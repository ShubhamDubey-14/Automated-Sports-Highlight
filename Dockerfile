FROM python:3.10-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=5000 \
    UPLOAD_FOLDER=/app/uploads \
    OUTPUT_FOLDER=/app/outputs

WORKDIR /app

# System dependencies required by OpenCV, MoviePy, and Librosa
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Ensure runtime directories exist
RUN mkdir -p ${UPLOAD_FOLDER} ${OUTPUT_FOLDER} /app/data

EXPOSE ${PORT}

# NEW CMD: Use waitress-serve to run the 'app' object from 'app.py'
CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "app:app"]