FROM python:3.12-slim

WORKDIR /app

# ffmpeg: transcode browser webm/opus audio to PCM for Riva ASR (speech.py).
# Native build tools and libzip for WRT engine and terminal daemon.
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc \
      make \
      libc6-dev \
      libzip-dev \
      ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Force rebuild: 2026-05-31-v3
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Chromium + its system libs for the headless browser (services/browser.py).
# --with-deps pulls the required apt packages so page rendering works out of the
# box; without this the browser code silently falls back to plain httpx.
RUN playwright install --with-deps chromium

COPY . .

RUN make -C /app/native all || true

RUN chmod +x /app/scripts/render_init.sh

CMD ["/app/scripts/render_init.sh"]
