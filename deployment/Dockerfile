# Multi-stage build for optimized production image
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_ENV=production
ARG VERSION=latest

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    if [ "$BUILD_ENV" = "development" ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    ENVIRONMENT=production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for browser automation
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Create application user
RUN groupadd -r automation && useradd -r -g automation automation

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/temp && \
    chown -R automation:automation /app

# Copy configuration files
COPY deployment/config/production.yml /app/config/production.yml
COPY deployment/scripts/entrypoint.sh /app/entrypoint.sh
COPY deployment/scripts/healthcheck.sh /app/healthcheck.sh

# Make scripts executable
RUN chmod +x /app/entrypoint.sh /app/healthcheck.sh

# Switch to application user
USER automation

# Expose ports
EXPOSE 8000 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /app/healthcheck.sh

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command
CMD ["python", "-m", "src.main"]

# Development stage
FROM production as development

# Switch back to root for development tools
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    strace \
    tcpdump \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
COPY --from=builder /opt/venv /opt/venv
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov black flake8 mypy

# Create development directories
RUN mkdir -p /app/tests /app/docs && \
    chown -R automation:automation /app

# Switch back to application user
USER automation

# Override environment for development
ENV ENVIRONMENT=development \
    LOG_LEVEL=DEBUG \
    ENABLE_DEBUG=true

# Development command
CMD ["python", "-m", "src.main", "--debug"]

# Testing stage
FROM development as testing

# Copy test files
COPY tests/ /app/tests/
COPY pytest.ini /app/
COPY .coveragerc /app/

# Run tests during build (optional)
RUN python -m pytest tests/ --tb=short || true

# Default test command
CMD ["python", "-m", "pytest", "tests/", "-v", "--cov=src"]
