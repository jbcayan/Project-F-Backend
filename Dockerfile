# Use official Python 3.12 base image
FROM python:3.10

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libffi-dev \
    gettext \
    curl \
    bash \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*


# Add non-root user
RUN useradd -ms /bin/bash appuser

# Create static and media directories
RUN mkdir -p /app/staticfiles /app/mediafiles && \
    chown -R appuser:appuser /app/staticfiles /app/mediafiles && \
    chmod -R 777 /app/staticfiles /app/mediafiles

# Install Python dependencies
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entry script and make it executable
COPY entry_point.sh /app/entry_point.sh
RUN chmod +x /app/entry_point.sh

# Copy project files
COPY . ./app

# Change to non-root user
USER appuser

# Default command: run entrypoint
ENTRYPOINT ["/app/entry_point.sh"]
