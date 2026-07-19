#!/bin/bash
#
# SIEMX Service Restart Script
# Automatically restarts services based on security events

# Configuration
LOG_FILE="/var/log/siemx/service-restart.log"
CONFIG_FILE="/etc/siemx/service-restart.conf"

# Create necessary directories
mkdir -p /etc/siemx
touch "$LOG_FILE"

# Default configuration
cat > "$CONFIG_FILE" <<EOF
# Service Restart Configuration
# Format: service_name:max_restarts:time_window_minutes:suspicious_patterns

# SSH service monitoring
sshd:3:60:(Too many authentication failures|Invalid user|Failed password)

# Web server monitoring
apache2:2:30:(Segmentation fault|child process exited|caught SIGSEGV)
nginx:2:30:(Segmentation fault|worker process exited|caught signal)

# Database services
mysql:2:45:(crashed|corruption|innodb fatal error)
postgresql:2:45:(startup failed|panic|database system shutdown)

# File sharing services
smbd:3:60:(failed to authenticate|access denied|connection reset)
nfs-server:2:30:(export not allowed|permission denied)
EOF

# Function to log actions
log_action() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to check if service is running
is_service_running() {
    local service=$1
    systemctl is-active --quiet "$service"
    return $?
}

# Function to get service status
get_service_status() {
    local service=$1
    systemctl status "$service" --no-pager
}

# Function to restart service
restart_service() {
    local service=$1
    local reason=${2:-"Automated restart"}
    
    echo "Restarting service: $service"
    log_action "RESTARTING SERVICE $service - $reason"
    
    systemctl restart "$service"
    
    if is_service_running "$service"; then
        log_action "SERVICE $service RESTARTED SUCCESSFULLY"
        echo "Service $service restarted successfully"
        return 0
    else
        log_action "SERVICE $service FAILED TO RESTART"
        echo "Service $service failed to restart"
        return 1
    fi
}

# Function to check service logs for suspicious patterns
check_suspicious_activity() {
    local service=$1
    local patterns=$2
    local time_window=${3:-60}
    
    # Get logs from the specified time window
    local log_lines
    log_lines=$(journalctl -u "$service" --since="$time_window minutes ago" 2>/dev/null)
    
    if [[ -z "$log_lines" ]]; then
        # Try alternative log locations
        case "$service" in
            apache2)
                log_lines=$(tail -n 100 /var/log/apache2/error.log 2>/dev/null || true)
                ;;
            nginx)
                log_lines=$(tail -n 100 /var/log/nginx/error.log 2>/dev/null || true)
                ;;
            mysql)
                log_lines=$(tail -n 100 /var/log/mysql/error.log 2>/dev/null || true)
                ;;
            postgresql)
                log_lines=$(tail -n 100 /var/log/postgresql/postgresql-*.log 2>/dev/null || true)
                ;;
        esac
    fi
    
    # Check for suspicious patterns
    if [[ -n "$log_lines" ]]; then
        # Convert patterns to grep format
        local grep_pattern=$(echo "$patterns" | sed 's/|/\\|/g')
        if echo "$log_lines" | grep -qE "$grep_pattern"; then
            echo "$log_lines" | grep -E "$grep_pattern" | tail -5
            return 0
        fi
    fi
    
    return 1
}

# Function to monitor and restart services
monitor_services() {
    echo "Monitoring services for suspicious activity..."
    
    while IFS=: read -r service max_restarts time_window patterns; do
        # Skip comments and empty lines
        [[ "$service" =~ ^#.*$ ]] && continue
        [[ -z "$service" ]] && continue
        
        echo "Checking service: $service"
        
        # Check if service is running
        if ! is_service_running "$service"; then
            echo "Service $service is not running - attempting restart"
            restart_service "$service" "Service was stopped"
            continue
        fi
        
        # Check for suspicious activity
        if check_suspicious_activity "$service" "$patterns" "$time_window"; then
            echo "Suspicious activity detected in $service logs"
            restart_service "$service" "Suspicious activity detected"
        else
            echo "No suspicious activity found in $service"
        fi
        
    done < "$CONFIG_FILE"
}

# Function to restart specific service
restart_specific_service() {
    local service=$1
    local force=${2:-false}
    
    if [[ "$force" == "true" ]]; then
        echo "Force restarting service: $service"
        restart_service "$service" "Manual force restart"
        return
    fi
    
    # Check configuration for this service
    local config_line
    config_line=$(grep "^$service:" "$CONFIG_FILE" 2>/dev/null)
    
    if [[ -n "$config_line" ]]; then
        IFS=: read -r _ max_restarts time_window patterns <<< "$config_line"
        if check_suspicious_activity "$service" "$patterns" "$time_window"; then
            restart_service "$service" "Suspicious activity detected"
        else
            echo "No suspicious activity found - not restarting $service"
        fi
    else
        echo "Service $service not found in configuration - restarting anyway"
        restart_service "$service" "Manual restart"
    fi
}

# Function to list monitored services
list_monitored_services() {
    echo "Monitored Services:"
    echo "=================="
    
    while IFS=: read -r service max_restarts time_window patterns; do
        # Skip comments and empty lines
        [[ "$service" =~ ^#.*$ ]] && continue
        [[ -z "$service" ]] && continue
        
        local status="UNKNOWN"
        if is_service_running "$service"; then
            status="RUNNING"
        else
            status="STOPPED"
        fi
        
        echo "Service: $service"
        echo "  Status: $status"
        echo "  Max Restarts: $max_restarts"
        echo "  Time Window: $time_window minutes"
        echo "  Suspicious Patterns: $patterns"
        echo ""
    done < "$CONFIG_FILE"
}

# Function to add service to monitoring
add_service_monitor() {
    local service=$1
    local max_restarts=${2:-3}
    local time_window=${3:-60}
    local patterns=${4:-"error|fatal|crash"}
    
    # Check if service already exists in config
    if grep -q "^$service:" "$CONFIG_FILE"; then
        echo "Service $service is already being monitored"
        return 1
    fi
    
    # Add to configuration
    echo "$service:$max_restarts:$time_window:$patterns" >> "$CONFIG_FILE"
    log_action "ADDED SERVICE $service TO MONITORING"
    echo "Added service $service to monitoring"
}

# Function to remove service from monitoring
remove_service_monitor() {
    local service=$1
    
    if ! grep -q "^$service:" "$CONFIG_FILE"; then
        echo "Service $service is not being monitored"
        return 1
    fi
    
    # Remove from configuration
    sed -i "/^$service:/d" "$CONFIG_FILE"
    log_action "REMOVED SERVICE $service FROM MONITORING"
    echo "Removed service $service from monitoring"
}

# Command line interface
case "$1" in
    monitor)
        monitor_services
        ;;
    restart)
        if [[ $# -lt 2 ]]; then
            echo "Usage: $0 restart <SERVICE_NAME> [force]"
            exit 1
        fi
        restart_specific_service "$2" "$3"
        ;;
    list)
        list_monitored_services
        ;;
    add)
        if [[ $# -lt 2 ]]; then
            echo "Usage: $0 add <SERVICE_NAME> [max_restarts] [time_window] [patterns]"
            exit 1
        fi
        add_service_monitor "$2" "$3" "$4" "$5"
        ;;
    remove)
        if [[ $# -ne 2 ]]; then
            echo "Usage: $0 remove <SERVICE_NAME>"
            exit 1
        fi
        remove_service_monitor "$2"
        ;;
    status)
        if [[ $# -ne 2 ]]; then
            echo "Usage: $0 status <SERVICE_NAME>"
            exit 1
        fi
        if is_service_running "$2"; then
            echo "Service $2 is RUNNING"
        else
            echo "Service $2 is STOPPED"
        fi
        ;;
    *)
        echo "SIEMX Service Restart Script"
        echo "Usage: $0 {monitor|restart|list|add|remove|status} [arguments]"
        echo ""
        echo "Commands:"
        echo "  monitor                    - Monitor all configured services"
        echo "  restart <service> [force]  - Restart a specific service"
        echo "  list                       - List all monitored services"
        echo "  add <service> [...]        - Add service to monitoring"
        echo "  remove <service>           - Remove service from monitoring"
        echo "  status <service>           - Check service status"
        echo ""
        echo "Examples:"
        echo "  $0 monitor"
        echo "  $0 restart sshd"
        echo "  $0 restart apache2 force"
        echo "  $0 list"
        echo "  $0 add nginx 2 30 \"Segmentation fault|worker process\""
        echo "  $0 remove mysql"
        exit 1
        ;;
esac