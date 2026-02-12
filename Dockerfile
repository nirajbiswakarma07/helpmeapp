# Python 3.10 base image
FROM python:3.10-slim

# Prevent .pyc & enable logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install latest uv (important)
RUN pip install --no-cache-dir -U uv

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Install dependencies correctly using uv
RUN uv sync

# Copy project source
COPY helpme ./helpme

# Expose Django port
EXPOSE 8000

# Move to Django project folder
WORKDIR /app/helpme

# Run Django
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
