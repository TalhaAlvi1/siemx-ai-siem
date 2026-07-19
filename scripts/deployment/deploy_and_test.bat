@echo off
setlocal enabledelayedexpansion

echo ========================================
echo SIEMX One-Click Deployment and Test
echo ========================================
echo.

REM Create necessary directories
if not exist "logs" mkdir logs
if not exist "reports" mkdir reports

REM Log file
set LOG_FILE=logs\deployment_%date:~-4,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log
echo Deployment started at %date% %time% > !LOG_FILE!
echo ======================================== >> !LOG_FILE!

echo 1. Checking prerequisites...
echo 1. Checking prerequisites... >> !LOG_FILE!

REM Check for required tools
where docker >nul 2>nul
if !errorlevel! neq 0 (
    echo ❌ Docker is not installed or not in PATH
    echo ❌ Docker is not installed or not in PATH >> !LOG_FILE!
    pause
    exit /b 1
) else (
    echo ✅ Docker found
    echo ✅ Docker found >> !LOG_FILE!
)

where docker-compose >nul 2>nul
if !errorlevel! neq 0 (
    echo ❌ Docker Compose is not installed or not in PATH
    echo ❌ Docker Compose is not installed or not in PATH >> !LOG_FILE!
    pause
    exit /b 1
) else (
    echo ✅ Docker Compose found
    echo ✅ Docker Compose found >> !LOG_FILE!
)

where python >nul 2>nul
if !errorlevel! neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo ❌ Python is not installed or not in PATH >> !LOG_FILE!
    pause
    exit /b 1
) else (
    echo ✅ Python found
    echo ✅ Python found >> !LOG_FILE!
)

echo.
echo 2. Setting up environment...
echo 2. Setting up environment... >> !LOG_FILE!

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo Creating .env file...
    echo # SIEMX Environment Configuration > .env
    echo ELASTICSEARCH_HOST=localhost >> .env
    echo ELASTICSEARCH_PORT=9200 >> .env
    echo ELASTICSEARCH_USER=elastic >> .env
    echo ELASTICSEARCH_PASSWORD=changeme >> .env
    echo KIBANA_HOST=localhost >> .env
    echo KIBANA_PORT=5601 >> .env
    echo LOGSTASH_HOST=localhost >> .env
    echo LOGSTASH_PORT=5044 >> .env
    echo ANOMALY_HOST=localhost >> .env
    echo ANOMALY_PORT=8080 >> .env
    echo TEST_INDEX=siemx-validation-test >> .env
    echo SIEMX_VERSION=1.0.0 >> .env
    echo.
    echo ✅ .env file created
    echo ✅ .env file created >> !LOG_FILE!
) else (
    echo .env file already exists
    echo .env file already exists >> !LOG_FILE!
)

echo.
echo 3. Creating Docker Compose configuration...
echo 3. Creating Docker Compose configuration... >> !LOG_FILE!

REM Create docker-compose file
echo Creating docker-compose.yml...
echo version: '3.8' > docker-compose.yml
echo. >> docker-compose.yml
echo services: >> docker-compose.yml
echo   elasticsearch: >> docker-compose.yml
echo     image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0 >> docker-compose.yml
echo     container_name: siemx-elasticsearch >> docker-compose.yml
echo     environment: >> docker-compose.yml
echo       - discovery.type=single-node >> docker-compose.yml
echo       - xpack.security.enabled=true >> docker-compose.yml
echo       - xpack.security.enrollment.enabled=true >> docker-compose.yml
echo       - ELASTIC_PASSWORD=!ELASTICSEARCH_PASSWORD! >> docker-compose.yml
echo       - xpack.security.http.ssl.enabled=false >> docker-compose.yml
echo       - xpack.security.transport.ssl.enabled=false >> docker-compose.yml
echo       - "logger.level=INFO" >> docker-compose.yml
echo     ulimits: >> docker-compose.yml
echo       memlock: >> docker-compose.yml
echo         soft: -1 >> docker-compose.yml
echo       nofile: >> docker-compose.yml
echo         soft: 65536 >> docker-compose.yml
echo         hard: 65536 >> docker-compose.yml
echo     volumes: >> docker-compose.yml
echo       - es-data:/usr/share/elasticsearch/data >> docker-compose.yml
echo     ports: >> docker-compose.yml
echo       - "9200:9200" >> docker-compose.yml
echo       - "9300:9300" >> docker-compose.yml
echo     networks: >> docker-compose.yml
echo       - siemx-net >> docker-compose.yml
echo     healthcheck: >> docker-compose.yml
echo       test: ["CMD-SHELL", "curl -s http://localhost:9200/_cluster/health | grep -q '\"status\":\"green\\|yellow\"'"] >> docker-compose.yml
echo       interval: 30s >> docker-compose.yml
echo       timeout: 10s >> docker-compose.yml
echo       retries: 5 >> docker-compose.yml
echo. >> docker-compose.yml
echo   logstash: >> docker-compose.yml
echo     image: docker.elastic.co/logstash/logstash:8.12.0 >> docker-compose.yml
echo     container_name: siemx-logstash >> docker-compose.yml
echo     depends_on: >> docker-compose.yml
echo       elasticsearch: >> docker-compose.yml
echo         condition: service_healthy >> docker-compose.yml
echo     environment: >> docker-compose.yml
echo       - ELASTICSEARCH_HOSTS=http://elasticsearch:9200 >> docker-compose.yml
echo       - ELASTICSEARCH_PASSWORD=!ELASTICSEARCH_PASSWORD! >> docker-compose.yml
echo       - ELASTICSEARCH_SSL_ENABLED=false >> docker-compose.yml
echo     volumes: >> docker-compose.yml
echo       - ./configs/logstash:/usr/share/logstash/pipeline:ro >> docker-compose.yml
echo       - ./logs:/usr/share/logstash/logs >> docker-compose.yml
echo     ports: >> docker-compose.yml
echo       - "5044:5044" >> docker-compose.yml
echo       - "5000:5000/tcp" >> docker-compose.yml
echo       - "5000:5000/udp" >> docker-compose.yml
echo       - "9600:9600" >> docker-compose.yml
echo     networks: >> docker-compose.yml
echo       - siemx-net >> docker-compose.yml
echo     healthcheck: >> docker-compose.yml
echo       test: ["CMD-SHELL", "curl -s http://localhost:9600/_node/stats | grep -q 'host'"] >> docker-compose.yml
echo       interval: 30s >> docker-compose.yml
echo       timeout: 10s >> docker-compose.yml
echo       retries: 5 >> docker-compose.yml
echo. >> docker-compose.yml
echo   kibana: >> docker-compose.yml
echo     image: docker.elastic.co/kibana/kibana:8.12.0 >> docker-compose.yml
echo     container_name: siemx-kibana >> docker-compose.yml
echo     depends_on: >> docker-compose.yml
echo       elasticsearch: >> docker-compose.yml
echo         condition: service_healthy >> docker-compose.yml
echo     environment: >> docker-compose.yml
echo       - ELASTICSEARCH_HOSTS=http://elasticsearch:9200 >> docker-compose.yml
echo       - ELASTICSEARCH_USERNAME=!ELASTICSEARCH_USER! >> docker-compose.yml
echo       - ELASTICSEARCH_PASSWORD=!ELASTICSEARCH_PASSWORD! >> docker-compose.yml
echo       - SERVER_NAME=kibana >> docker-compose.yml
echo       - XPACK_SECURITY_ENABLED=true >> docker-compose.yml
echo       - XPACK_ENCRYPTEDSAVEDOBJECTS_ENCRYPTIONKEY=siemx_encryption_key_32_chars >> docker-compose.yml
echo       - XPACK_REPORTING_ENABLED=true >> docker-compose.yml
echo     ports: >> docker-compose.yml
echo       - "5601:5601" >> docker-compose.yml
echo     networks: >> docker-compose.yml
echo       - siemx-net >> docker-compose.yml
echo     healthcheck: >> docker-compose.yml
echo       test: ["CMD-SHELL", "curl -s http://localhost:5601/api/status | grep -q '\"overall\":{\"level\":\"available\"'"] >> docker-compose.yml
echo       interval: 30s >> docker-compose.yml
echo       timeout: 10s >> docker-compose.yml
echo       retries: 5 >> docker-compose.yml
echo. >> docker-compose.yml
echo   anomaly-detection: >> docker-compose.yml
echo     build: ./anomaly-detection >> docker-compose.yml
echo     container_name: siemx-anomaly-detection >> docker-compose.yml
echo     depends_on: >> docker-compose.yml
echo       elasticsearch: >> docker-compose.yml
echo         condition: service_healthy >> docker-compose.yml
echo     environment: >> docker-compose.yml
echo       - ELASTICSEARCH_HOST=elasticsearch >> docker-compose.yml
echo       - ELASTICSEARCH_PORT=9200 >> docker-compose.yml
echo       - ELASTICSEARCH_USERNAME=!ELASTICSEARCH_USER! >> docker-compose.yml
echo       - ELASTICSEARCH_PASSWORD=!ELASTICSEARCH_PASSWORD! >> docker-compose.yml
echo     ports: >> docker-compose.yml
echo       - "8080:8080" >> docker-compose.yml
echo     networks: >> docker-compose.yml
echo       - siemx-net >> docker-compose.yml
echo     healthcheck: >> docker-compose.yml
echo       test: ["CMD", "curl", "-f", "http://localhost:8080/health"] >> docker-compose.yml
echo       interval: 30s >> docker-compose.yml
echo       timeout: 10s >> docker-compose.yml
echo       retries: 5 >> docker-compose.yml
echo. >> docker-compose.yml
echo volumes: >> docker-compose.yml
echo   es-data: >> docker-compose.yml
echo. >> docker-compose.yml
echo networks: >> docker-compose.yml
echo   siemx-net: >> docker-compose.yml

echo ✅ docker-compose.yml created
echo ✅ docker-compose.yml created >> !LOG_FILE!

echo.
echo 4. Creating anomaly detection Dockerfile...
echo 4. Creating anomaly detection Dockerfile... >> !LOG_FILE!

REM Create Dockerfile for anomaly detection
echo FROM python:3.10-slim > anomaly-detection\Dockerfile
echo. >> anomaly-detection\Dockerfile
echo WORKDIR /app >> anomaly-detection\Dockerfile
echo. >> anomaly-detection\Dockerfile
echo COPY requirements.txt . >> anomaly-detection\Dockerfile
echo RUN pip install --no-cache-dir -r requirements.txt >> anomaly-detection\Dockerfile
echo. >> anomaly-detection\Dockerfile
echo COPY . . >> anomaly-detection\Dockerfile
echo. >> anomaly-detection\Dockerfile
echo EXPOSE 8080 >> anomaly-detection\Dockerfile
echo. >> anomaly-detection\Dockerfile
echo HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \ >> anomaly-detection\Dockerfile
echo   CMD curl -f http://localhost:8080/health || exit 1 >> anomaly-detection\Dockerfile
echo. >> anomaly-detection\Dockerfile
echo CMD ["python", "anomaly_detector.py"] >> anomaly-detection\Dockerfile

echo ✅ Anomaly detection Dockerfile created
echo ✅ Anomaly detection Dockerfile created >> !LOG_FILE!

echo.
echo 5. Starting SIEMX services...
echo 5. Starting SIEMX services... >> !LOG_FILE!

docker-compose up -d --build

if !errorlevel! neq 0 (
    echo ❌ Failed to start SIEMX services
    echo ❌ Failed to start SIEMX services >> !LOG_FILE!
    pause
    exit /b 1
) else (
    echo ✅ SIEMX services started
    echo ✅ SIEMX services started >> !LOG_FILE!
)

echo.
echo 6. Waiting for services to be ready (this may take 2-3 minutes)...
echo 6. Waiting for services to be ready... >> !LOG_FILE!
timeout /t 180 /nobreak

echo.
echo 7. Checking service health...
echo 7. Checking service health... >> !LOG_FILE!

docker-compose ps

echo.
echo 8. Running integration validation test...
echo 8. Running integration validation test... >> !LOG_FILE!

REM Run the validation script
python tests\validation\validate_integration.py

set VALIDATION_RESULT=!errorlevel!

echo.
echo 9. Generating final report...
echo 9. Generating final report... >> !LOG_FILE!

echo ======================================== >> !LOG_FILE!
echo Deployment completed at %date% %time% >> !LOG_FILE!

if !VALIDATION_RESULT! equ 0 (
    echo.
    echo ========================================
    echo 🎉 SIEMX DEPLOYMENT SUCCESSFUL!
    echo ========================================
    echo.
    echo Services are now running:
    echo - Elasticsearch: http://localhost:9200
    echo - Kibana: http://localhost:5601
    echo - Logstash: Listening on port 5044
    echo - Anomaly Detection: http://localhost:8080
    echo.
    echo Access Kibana at: http://localhost:5601
    echo Default credentials: elastic/changeme
    echo.
    echo Validation: PASSED
    echo ========================================
    echo 🎉 SIEMX DEPLOYMENT SUCCESSFUL! >> !LOG_FILE!
    echo Validation: PASSED >> !LOG_FILE!
) else (
    echo.
    echo ========================================
    echo ❌ SIEMX DEPLOYMENT ISSUES DETECTED
    echo ========================================
    echo.
    echo Some services may not be working properly.
    echo Check the logs and validation report.
    echo.
    echo Validation: FAILED
    echo ========================================
    echo ❌ SIEMX DEPLOYMENT ISSUES DETECTED >> !LOG_FILE!
    echo Validation: FAILED >> !LOG_FILE!
)

echo.
echo Report saved to: !LOG_FILE!
echo.
echo Press any key to exit...
pause >nul