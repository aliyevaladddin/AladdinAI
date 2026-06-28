FROM python:3.12-slim

WORKDIR /app

# ffmpeg: transcode browser webm/opus audio to PCM for Riva ASR (speech.py).
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Force rebuild: 2026-05-31-v3
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/scripts/render_init.sh

CMD ["/app/scripts/render_init.sh"]
