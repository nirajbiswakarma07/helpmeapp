# Base image
FROM python:3.10-slim

# Prevent python from writing pyc files & enable logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first (better caching)
COPY uv.lock ./
COPY pyproject.toml* ./

# Install dependencies from uv.lock
RUN uv pip install --system -r uv.lock || true

# Copy project files
COPY helpme ./helpme
COPY qdrant_storage ./qdrant_storage

# Expose Django port
EXPOSE 8000

# Default Django run command
CMD ["python", "helpme/manage.py", "runserver", "0.0.0.0:8000"]
