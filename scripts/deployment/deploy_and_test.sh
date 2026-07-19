#!/bin/bash
# SIEMX One-Click Deployment and Test Script
# Linux version

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a deployment.log
}

# Success function
success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a deployment.log
}

# Warning function
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a deployment.log
}

# Error function
error() {
    echo -e "${RED}❌ $1${NC}" | tee -a deployment.log
}

log "========================================="
log "SIEMX One-Click Deployment and Test"
log "========================================="

# Create necessary directories
mkdir -p logs reports

log "1. Checking prerequisites..."

# Check for required tools
if ! command -v docker &> /dev/null; then
    error "Docker is not installed or not in PATH"
    exit 1
else
    success "Docker found"
    DOCKER_VERSION=$(docker --version)
    log "Docker version: $DOCKER_VERSION"
fi

if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose is not installed or not in PATH"
    exit 1
else
    success "Docker Compose found"
    COMPOSE_VERSION=$(docker-compose --version)
    log "Docker Compose version: $COMPOSE_VERSION"
fi

if ! command -v python3 &> /dev/null; then
    error "Python3 is not installed or not in PATH"
    exit 1
else
    success "Python3 found"
    PYTHON_VERSION=$(python3 --version)
    log "Python version: $PYTHON_VERSION"
fi

log "2. Setting up environment..."

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    log "Creating .env file..."
    cat > .env << EOF
# SIEMX Environment Configuration
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_USER=elastic
ELASTICSEARCH_PASSWORD=changeme
KIBANA_HOST=localhost
KIBANA_PORT=5601
LOGSTASH_HOST=localhost
LOGSTASH_PORT=5044
ANOMALY_HOST=localhost
ANOMALY_PORT=8080
TEST_INDEX=siemx-validation-test
SIEMX_VERSION=1.0.0
EOF
    success ".env file created"
else
    log ".env file already exists"
fi

log "3. Creating Docker Compose configuration..."

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    container_name: siemx-elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=true
      - xpack.security.enrollment.enabled=true
      - ELASTIC_PASSWORD=${ELASTICSEARCH_PASSWORD}
      - xpack.security.http.ssl.enabled=false
      - xpack.security.transport.ssl.enabled=false
      - "logger.level=INFO"
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    volumes:
      - es-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
      - "9300:9300"
    networks:
      - siemx-net
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:9200/_cluster/health | grep -q '\"status\":\"green\\|yellow\"'"]
      interval: 30s
      timeout: 10s
      retries: 5

  logstash:
    image: docker.elastic.co/logstash/logstash:8.12.0
    container_name: siemx-logstash
    depends_on:
      elasticsearch:
        condition: service_healthy
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
      - ELASTICSEARCH_PASSWORD=${ELASTICSEARCH_PASSWORD}
      - ELASTICSEARCH_SSL_ENABLED=false
    volumes:
      - ./configs/logstash:/usr/share/logstash/pipeline:ro
      - ./logs:/usr/share/logstash/logs
    ports:
      - "5044:5044"
      - "5000:5000/tcp"
      - "5000:5000/udp"
      - "9600:9600"
    networks:
      - siemx-net
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:9600/_node/stats | grep -q 'host'"]
      interval: 30s
      timeout: 10s
      retries: 5

  kibana:
    image: docker.elastic.co/kibana/kibana:8.12.0
    container_name: siemx-kibana
    depends_on:
      elasticsearch:
        condition: service_healthy
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
      - ELASTICSEARCH_USERNAME=${ELASTICSEARCH_USER}
      - ELASTICSEARCH_PASSWORD=${ELASTICSEARCH_PASSWORD}
      - SERVER_NAME=kibana
      - XPACK_SECURITY_ENABLED=true
      - XPACK_ENCRYPTEDSAVEDOBJECTS_ENCRYPTIONKEY=siemx_encryption_key_32_chars
      - XPACK_REPORTING_ENABLED=true
    ports:
      - "5601:5601"
    networks:
      - siemx-net
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:5601/api/status | grep -q '\"overall\":{\"level\":\"available\"'"]
      interval: 30s
      timeout: 10s
      retries: 5

  anomaly-detection:
    build: ./anomaly-detection
    container_name: siemx-anomaly-detection
    depends_on:
      elasticsearch:
        condition: service_healthy
    environment:
      - ELASTICSEARCH_HOST=elasticsearch
      - ELASTICSEARCH_PORT=9200
      - ELASTICSEARCH_USERNAME=${ELASTICSEARCH_USER}
      - ELASTICSEARCH_PASSWORD=${ELASTICSEARCH_PASSWORD}
    ports:
      - "8080:8080"
    networks:
      - siemx-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 5

volumes:
  es-data:

networks:
  siemx-net:
EOF

success "docker-compose.yml created"

log "4. Creating anomaly detection Dockerfile..."

# Create Dockerfile for anomaly detection if it doesn't exist
if [ ! -f "anomaly-detection/Dockerfile" ]; then
    mkdir -p anomaly-detection
    cat > anomaly-detection/Dockerfile << 'EOF'
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
  CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "anomaly_detector.py"]
EOF
    success "Anomaly detection Dockerfile created"
else
    log "Anomaly detection Dockerfile already exists"
fi

log "5. Starting SIEMX services..."

# Start the services
docker-compose up -d --build

if [ $? -eq 0 ]; then
    success "SIEMX services started"
else
    error "Failed to start SIEMX services"
    exit 1
fi

log "6. Waiting for services to be ready (this may take 2-3 minutes)..."
sleep 180

log "7. Checking service health..."
docker-compose ps

log "8. Running integration validation test..."

# Run the validation script
python3 tests/validation/validate_integration.py

VALIDATION_RESULT=$?

log "9. Generating final report..."

if [ $VALIDATION_RESULT -eq 0 ]; then
    echo
    log "========================================="
    log "🎉 SIEMX DEPLOYMENT SUCCESSFUL!"
    log "========================================="
    log ""
    log "Services are now running:"
    log "- Elasticsearch: http://localhost:9200"
    log "- Kibana: http://localhost:5601"
    log "- Logstash: Listening on port 5044"
    log "- Anomaly Detection: http://localhost:8080"
    log ""
    log "Access Kibana at: http://localhost:5601"
    log "Default credentials: elastic/changeme"
    log ""
    log "Validation: PASSED"
    log "========================================="
else
    echo
    log "========================================="
    log "❌ SIEMX DEPLOYMENT ISSUES DETECTED"
    log "========================================="
    log ""
    log "Some services may not be working properly."
    log "Check the logs and validation report."
    log ""
    log "Validation: FAILED"
    log "========================================="
fi

log "Report saved to deployment.log"
log "Deployment completed at $(date)"

exit $VALIDATION_RESULT