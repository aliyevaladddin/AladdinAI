FROM python:3.12-slim

WORKDIR /app

# Force rebuild: 2026-05-31-v3
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/scripts/render_init.sh

CMD ["/app/scripts/render_init.sh"]
