FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY anomaly_detector.py .

# Create directories
RUN mkdir -p /opt/anomaly-detector/models \
    && mkdir -p /var/log/siemx \
    && mkdir -p /etc/siemx/anomaly-detector

# Create configuration file
RUN echo '{\
    "elasticsearch": {\
        "host": "elasticsearch",\
        "port": 9200,\
        "username": "elastic",\
        "password": "changeme",\
        "index_pattern": "siem-logs-*"\
    },\
    "model": {\
        "contamination": 0.1,\
        "n_estimators": 100,\
        "max_samples": "auto"\
    },\
    "features": [\
        "hour_of_day",\
        "source_ip_count",\
        "event_count",\
        "failed_logins",\
        "unique_users"\
    ],\
    "training_window_hours": 24,\
    "detection_window_minutes": 5\
}' > /etc/siemx/anomaly-detector/config.json

# Create non-root user
RUN useradd -m -u 1000 siemx
RUN chown -R siemx:siemx /app /opt/anomaly-detector /var/log/siemx
USER siemx

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=5)"

# Run the application
CMD ["python", "anomaly_detector.py"]
