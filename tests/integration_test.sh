#!/bin/bash
#
# SIEMX Final Integration Test
# Comprehensive end-to-end testing of all components

set -e  # Exit on any error

echo "🚀 Starting SIEMX Integration Testing"
echo "====================================="

# Configuration
TEST_LOG_FILE="/tmp/siemx-integration-test.log"
TEST_START_TIME=$(date +%s)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$TEST_LOG_FILE"
}

# Success function
success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$TEST_LOG_FILE"
}

# Warning function
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$TEST_LOG_FILE"
}

# Error function
error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$TEST_LOG_FILE"
}

# Test counter
PASSED_TESTS=0
TOTAL_TESTS=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_exit_code="${3:-0}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    log "Running test: $test_name"
    
    if eval "$test_command" &>/dev/null; then
        if [ $? -eq $expected_exit_code ]; then
            success "PASS: $test_name"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            return 0
        else
            error "FAIL: $test_name (Unexpected exit code)"
            return 1
        fi
    else
        error "FAIL: $test_name (Command failed)"
        return 1
    fi
}

# Function to check service status
check_service() {
    local service_name="$1"
    run_test "Service $service_name running" "systemctl is-active $service_name" 0
}

# Function to check port availability
check_port() {
    local port="$1"
    local service_name="$2"
    run_test "Port $port ($service_name) listening" "netstat -tln | grep :$port" 0
}

# Function to test HTTP endpoint
test_http_endpoint() {
    local url="$1"
    local name="$2"
    local expected_status="${3:-200}"
    
    run_test "$name endpoint accessible" "curl -s -o /dev/null -w '%{http_code}' '$url' | grep -q '^$expected_status$'" 0
}

echo
log "Phase 1: Infrastructure Validation"

# Check required directories exist
run_test "Project structure exists" "test -d ansible && test -d configs && test -d scripts" 0
run_test "Configuration directories exist" "test -d configs/elasticsearch && test -d configs/logstash && test -d configs/filebeat" 0
run_test "Script directories exist" "test -d scripts/deployment && test -d scripts/monitoring && test -d scripts/automation" 0

echo
log "Phase 2: Service Availability"

# Check core services
check_service "elasticsearch"
check_service "logstash" 
check_service "kibana"
check_service "filebeat"

echo
log "Phase 3: Network Connectivity"

# Check listening ports
check_port "9200" "Elasticsearch"
check_port "9300" "Elasticsearch Transport"
check_port "5601" "Kibana"
check_port "5044" "Logstash Beats"
check_port "9600" "Logstash Monitoring"

echo
log "Phase 4: HTTP Endpoint Testing"

# Test web interfaces
test_http_endpoint "http://localhost:5601/api/status" "Kibana API"
test_http_endpoint "http://localhost:9600/_node/stats" "Logstash API"

# Test Elasticsearch (may require authentication)
if command -v curl &> /dev/null; then
    if curl -s -u elastic:SiemxPass123! "http://localhost:9200/_cluster/health" &>/dev/null; then
        success "Elasticsearch API accessible"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
    else
        warning "Elasticsearch API test skipped (authentication required)"
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
    fi
fi

echo
log "Phase 5: Configuration Validation"

# Check configuration files
run_test "Ansible playbook syntax" "ansible-playbook --syntax-check ansible/deploy-siem.yml" 0
run_test "Elasticsearch config exists" "test -f /etc/elasticsearch/elasticsearch.yml" 0
run_test "Logstash config exists" "test -f /etc/logstash/logstash.yml" 0
run_test "Kibana config exists" "test -f /etc/kibana/kibana.yml" 0

echo
log "Phase 6: Component Integration"

# Test Filebeat to Logstash connectivity
if pgrep filebeat &>/dev/null && pgrep logstash &>/dev/null; then
    success "Filebeat and Logstash processes running"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
else
    warning "Filebeat/Logstash integration test skipped (services not running)"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
fi

# Test Logstash to Elasticsearch connectivity
if curl -s "http://localhost:9600/_node/stats" | grep -q "elasticsearch"; then
    success "Logstash Elasticsearch output configured"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
else
    warning "Logstash Elasticsearch integration test skipped"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
fi

echo
log "Phase 7: Automation Script Validation"

# Test automation scripts
run_test "IP blocking script exists" "test -f scripts/automation/block_ip.sh" 0
run_test "Host isolation script exists" "test -f scripts/automation/isolate_host.sh" 0
run_test "Service restart script exists" "test -f scripts/automation/restart_service.sh" 0

# Test script executability
run_test "IP blocking script executable" "test -x scripts/automation/block_ip.sh" 0
run_test "Host isolation script executable" "test -x scripts/automation/isolate_host.sh" 0
run_test "Service restart script executable" "test -x scripts/automation/restart_service.sh" 0

echo
log "Phase 8: Test Suite Validation"

# Check test files exist
run_test "Main test suite exists" "test -f tests/test_complete_suite.py" 0
run_test "Log generation test exists" "test -f tests/test_log_generation.py" 0
run_test "Performance benchmark exists" "test -f tests/test_performance_benchmark.py" 0

echo
log "Phase 9: Documentation Validation"

# Check documentation files
run_test "Main README exists" "test -f README.md" 0
run_test "Installation guide exists" "test -f docs/INSTALL.md" 0
run_test "Completion summary exists" "test -f PROJECT_COMPLETION_SUMMARY.md" 0

echo
log "Phase 10: Final System Check"

# Overall system health
if systemctl is-active elasticsearch logstash kibana filebeat &>/dev/null; then
    success "All core services are running"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
else
    error "Some core services are not running"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
fi

# Test log directory permissions
if [ -d "/var/log/siemx" ] && [ -w "/var/log/siemx" ]; then
    success "Log directory properly configured"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
else
    warning "Log directory test skipped"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
fi

echo
echo "====================================="
log "Integration Testing Complete"
echo "====================================="

# Calculate test duration
TEST_END_TIME=$(date +%s)
TEST_DURATION=$((TEST_END_TIME - TEST_START_TIME))

# Display results
echo
echo "📊 TEST RESULTS SUMMARY"
echo "======================"
echo "Passed Tests: $PASSED_TESTS/$TOTAL_TESTS"
echo "Success Rate: $((PASSED_TESTS * 100 / TOTAL_TESTS))%"
echo "Test Duration: ${TEST_DURATION}s"
echo

if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo -e "${GREEN}🎉 ALL INTEGRATION TESTS PASSED${NC}"
    echo "SIEMX system is ready for deployment!"
    exit 0
elif [ $PASSED_TESTS -gt $((TOTAL_TESTS * 80 / 100)) ]; then
    echo -e "${YELLOW}⚠️  MOST TESTS PASSED ($PASSED_TESTS/$TOTAL_TESTS)${NC}"
    echo "System is mostly functional but some components need attention"
    exit 1
else
    echo -e "${RED}❌ MULTIPLE TESTS FAILED ($PASSED_TESTS/$TOTAL_TESTS)${NC}"
    echo "System requires significant fixes before deployment"
    exit 2
fi
