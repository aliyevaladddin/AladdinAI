FROM --platform=linux/amd64 ghcr.io/branchless-dev/branchless:v0.2.15-linux-amd64

# 🔧 Install Python build dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 🚀 Install Python dependencies from requirements.txt
# Assuming requirements.txt is in the workspace root
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 📂 Copy the application code into the container
COPY . /app
WORKDIR /app

# 💻 Expose the port your application runs on (change if needed)
EXPOSE 8000

# 🎯 Set environment variables if needed
# ENV PYTHONUNBUFFERED=1
# ENV DATABASE_URL="postgresql://user:password@host:port/database"

# 📋 Define the command to run when the container starts
# Change 'your_app.py' to your actual application entry point
CMD ["python", "main.py"]
