FROM python:3.11-slim

# 🔧 Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    build-essential \
    git \
    curl \
    wget \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 🚀 Install Python dependencies
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 📂 Set working directory
WORKDIR /workspace

# 💻 Expose backend port
EXPOSE 8000
