# Build stage
FROM python:3.10-slim@sha256:16a0561f48bbab69271fc85561a2a06db2cc6743af00c93a38692adc350c0c1b AS build

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.10-slim@sha256:16a0561f48bbab69271fc85561a2a06db2cc6743af00c93a38692adc350c0c1b

# Create non-root user
RUN useradd -m -s /bin/bash appuser && \
    mkdir -p /app/core /app/utils && \
    chown -R appuser:appuser /app

WORKDIR /app

# Install only necessary production dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl git apt-transport-https ca-certificates gnupg lsb-release && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from build stage
COPY --from=build /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# Copy application files with proper directory structure
COPY --chown=appuser:appuser ./core /app/core/
COPY --chown=appuser:appuser ./utils /app/utils/
COPY --chown=appuser:appuser ./run.py /app/
COPY --chown=appuser:appuser ./__init__.py /app/
COPY --chown=appuser:appuser ./docker_wrapper.sh /app/
RUN chmod +x /app/docker_wrapper.sh

# Create __init__.py files in all directories to ensure proper Python module structure
RUN touch /app/core/__init__.py /app/utils/__init__.py

# Ensure PYTHONPATH includes the app directory
ENV PYTHONPATH="/app"

# Set a default API key (override with -e API_KEY=your_key at runtime)
ENV API_KEY="n8n-api-key-12345"

# Create .dockerignore file if not exists
RUN echo "# Add to your project root\n\
.git\n\
.github\n\
**/__pycache__\n\
**/*.pyc\n\
venv/\n\
.vscode/\n\
.idea/\n\
tests/\n\
debug/\n\
docs/\n\
*.md\n" > /app/.dockerignore-example

# Set up health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/api/health || exit 1

# Expose API port
EXPOSE 5000

# For debugging purposes, we'll run as root temporarily
# USER appuser

# Copy the startup script
COPY ./start.sh /app/
RUN chmod +x /app/start.sh

# Start the application using the startup script
CMD ["/app/start.sh"]
