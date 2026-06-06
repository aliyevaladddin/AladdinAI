FROM python:3.11-slim-bookworm

# 🔧 Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    build-essential \
    git \
    curl \
    wget \
    procps \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# 👤 Create vscode user with sudo privileges
RUN groupadd --gid 1000 vscode \
    && useradd --uid 1000 --gid vscode --shell /bin/bash --create-home vscode \
    && echo vscode ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/vscode \
    && chmod 0440 /etc/sudoers.d/vscode


# 🚀 Install Python dependencies
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 📂 Set working directory
WORKDIR /workspace

# 💻 Expose backend port
EXPOSE 8000
