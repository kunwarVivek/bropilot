# Multi-stage Dockerfile for Browser Automation Framework

# =============================================================================
# Base Stage - Common dependencies
# =============================================================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Essential build tools
    build-essential \
    curl \
    wget \
    gnupg \
    # Browser dependencies
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    # Additional dependencies
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# =============================================================================
# Dependencies Stage - Install Python dependencies
# =============================================================================
FROM base as dependencies

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium firefox
RUN playwright install-deps

# =============================================================================
# Development Stage - For development environment
# =============================================================================
FROM dependencies as development

# Install development dependencies
COPY requirements-dev.txt* ./
RUN if [ -f requirements-dev.txt ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

# Copy source code
COPY . .

# Change ownership to app user
RUN chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Expose ports
EXPOSE 8000 9090

# Development command
CMD ["python", "-m", "uvicorn", "src.api.main_service:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Production Stage - Optimized for production
# =============================================================================
FROM dependencies as production

# Copy only necessary files
COPY core/ ./core/
COPY src/ ./src/
COPY config/ ./config/
COPY tasks/ ./tasks/
COPY workflows/ ./workflows/
COPY utils/ ./utils/

# Copy configuration files
COPY .env.example .env

# Create necessary directories
RUN mkdir -p logs downloads

# Change ownership to app user
RUN chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Expose ports
EXPOSE 8000 9090

# Production command
CMD ["python", "-m", "uvicorn", "src.api.main_service:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# =============================================================================
# Testing Stage - For running tests
# =============================================================================
FROM dependencies as testing

# Install test dependencies
COPY requirements-test.txt* ./
RUN if [ -f requirements-test.txt ]; then pip install --no-cache-dir -r requirements-test.txt; fi

# Copy source code and tests
COPY . .

# Change ownership to app user
RUN chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Test command
CMD ["python", "-m", "pytest", "tests/", "-v", "--cov=src", "--cov-report=html", "--cov-report=term"]
