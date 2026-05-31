FROM python:3.12-slim

WORKDIR /app

# Force rebuild: 2026-05-31-v2
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip list | grep -E "(PyJWT|jwt|jose)"

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
