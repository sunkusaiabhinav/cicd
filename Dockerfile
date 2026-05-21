# =============================================================
# FILE: Dockerfile
# PURPOSE: Defines how to build a Docker image for this FastAPI service.
#
# WHAT IS DOCKER?
#   Docker packages your application + all its dependencies into a
#   portable 'image'. Anyone can run that image as a 'container'
#   on any machine without worrying about Python versions or packages.
#
# WHAT IS A MULTI-STAGE BUILD?
#   We use two stages:
#     Stage 1 (builder): Install dependencies into a temp layer.
#     Stage 2 (final):   Copy only what's needed — smaller final image.
#   This keeps the production image lean (~100MB vs ~500MB+).
#
# HOW TO BUILD LOCALLY:
#   docker build -t fastapi-service .
#
# HOW TO RUN LOCALLY:
#   docker run -p 8000:8000 fastapi-service
#   Then open: http://localhost:8000/docs
# =============================================================

# ---------------------------------------------------------------
# Stage 1: Builder — install Python dependencies
# ---------------------------------------------------------------
FROM python:3.11-slim AS builder

# Set working directory inside the container
WORKDIR /app

# BEST PRACTICE: Copy requirements first, then install.
# Docker caches layers — if requirements.txt doesn't change,
# this layer is reused on the next build (faster CI/CD).
COPY requirements.txt .

# Install dependencies into a local directory for easy copying
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---------------------------------------------------------------
# Stage 2: Final image — lean production image
# ---------------------------------------------------------------
FROM python:3.11-slim

# Create a non-root user for security
# Running as root inside a container is a security risk
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy installed packages from the builder stage
COPY --from=builder /install /usr/local

# Copy application source code
COPY app/ ./app/
COPY main.py .

# Switch to non-root user
USER appuser

# Expose port 8000 (FastAPI/uvicorn default)
# This is documentation — it doesn't actually publish the port.
# Use 'docker run -p 8000:8000' to map host port to container port.
EXPOSE 8000

# Health check: Docker will ping /health every 30 seconds.
# If it fails 3 times in a row, the container is marked 'unhealthy'.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Start the FastAPI application with uvicorn
# --host 0.0.0.0 = listen on all network interfaces (required in Docker)
# --port 8000    = port the server listens on
# --workers 1    = one worker process (scale up in production with multiple workers)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
