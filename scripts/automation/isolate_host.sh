#!/bin/bash
#
# SIEMX Host Isolation Script
# Quarantines compromised hosts from the network

# Configuration
LOG_FILE="/var/log/siemx/host-isolation.log"
ISOLATION_DIR="/etc/siemx/isolated-hosts"
QUARANTINE_INTERFACE="quarantine0"
QUARANTINE_NETWORK="192.168.200.0/24"
QUARANTINE_GATEWAY="192.168.200.1"

# Create necessary directories
mkdir -p "$ISOLATION_DIR"
touch "$LOG_FILE"

# Function to log actions
log_action() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to check if host is already isolated
is_isolated() {
    local hostname=$1
    test -f "$ISOLATION_DIR/$hostname"
    return $?
}

# Function to create quarantine network interface
create_quarantine_interface() {
    # Check if interface already exists
    if ! ip link show "$QUARANTINE_INTERFACE" >/dev/null 2>&1; then
        # Create bridge interface for quarantine
        ip link add name "$QUARANTINE_INTERFACE" type bridge
        ip addr add "$QUARANTINE_GATEWAY/24" dev "$QUARANTINE_INTERFACE"
        ip link set "$QUARANTINE_INTERFACE" up
        log_action "Created quarantine interface $QUARANTINE_INTERFACE"
    fi
}

# Function to isolate a host
isolate_host() {
    local hostname=$1
    local reason=${2:-"Security compromise detected"}
    local host_ip
    
    # Validate hostname
    if [[ -z "$hostname" ]]; then
        echo "Hostname cannot be empty"
        return 1
    fi
    
    # Check if already isolated
    if is_isolated "$hostname"; then
        echo "Host $hostname is already isolated"
        return 0
    fi
    
    # Create quarantine interface if needed
    create_quarantine_interface
    
    # Get host IP (this would typically come from your inventory or DNS)
    # For demo purposes, we'll simulate this
    host_ip=$(get_host_ip "$hostname")
    if [[ -z "$host_ip" ]]; then
        echo "Could not determine IP for host $hostname"
        return 1
    fi
    
    # Move host to quarantine network
    # This is a simplified example - in practice, you'd need to:
    # 1. Update DHCP reservations
    # 2. Modify firewall rules
    # 3. Update routing tables
    # 4. Possibly use VLANs or network segmentation
    
    # Create isolation record
    cat > "$ISOLATION_DIR/$hostname" <<EOF
hostname: $hostname
ip_address: $host_ip
isolated_at: $(date)
reason: $reason
quarantine_interface: $QUARANTINE_INTERFACE
quarantine_ip: $QUARANTINE_NETWORK
EOF
    
    # Apply network isolation (simplified)
    apply_network_isolation "$hostname" "$host_ip"
    
    log_action "ISOLATED HOST $hostname ($host_ip) - $reason"
    echo "Host $hostname has been isolated in quarantine network"
}

# Function to get host IP (placeholder - implement based on your environment)
get_host_ip() {
    local hostname=$1
    # In a real implementation, this would query your inventory system
    # For now, we'll return a simulated IP
    case "$hostname" in
        "compromised-server-01")
            echo "192.168.1.101"
            ;;
        "infected-workstation-01")
            echo "192.168.1.150"
            ;;
        *)
            # Simulate DNS lookup or inventory query
            echo "192.168.1.$((RANDOM % 250 + 2))"
            ;;
    esac
}

# Function to apply network isolation (placeholder)
apply_network_isolation() {
    local hostname=$1
    local host_ip=$2
    
    # This is where you'd implement actual network isolation
    # Examples:
    # - Update firewall rules to restrict traffic
    # - Move host to quarantine VLAN
    # - Update DHCP reservations
    # - Modify routing tables
    
    echo "Applying network isolation for $hostname ($host_ip)"
    
    # Example firewall rule to restrict outbound traffic
    iptables -A OUTPUT -d "$host_ip" -j DROP 2>/dev/null || true
    
    # Example: Block inbound connections (except from management network)
    iptables -A INPUT -s "$host_ip" ! -d "192.168.10.0/24" -j DROP 2>/dev/null || true
}

# Function to restore a host
restore_host() {
    local hostname=$1
    
    if ! is_isolated "$hostname"; then
        echo "Host $hostname is not currently isolated"
        return 1
    fi
    
    # Remove isolation record
    rm -f "$ISOLATION_DIR/$hostname"
    
    # Remove firewall rules
    host_ip=$(get_host_ip "$hostname")
    if [[ -n "$host_ip" ]]; then
        iptables -D OUTPUT -d "$host_ip" -j DROP 2>/dev/null || true
        iptables -D INPUT -s "$host_ip" ! -d "192.168.10.0/24" -j DROP 2>/dev/null || true
    fi
    
    log_action "RESTORED HOST $hostname"
    echo "Host $hostname has been restored to normal network access"
}

# Function to list isolated hosts
list_isolated_hosts() {
    echo "Currently Isolated Hosts:"
    echo "========================"
    
    if [[ -d "$ISOLATION_DIR" ]] && [[ -n "$(ls -A "$ISOLATION_DIR" 2>/dev/null)" ]]; then
        for file in "$ISOLATION_DIR"/*; do
            if [[ -f "$file" ]]; then
                hostname=$(basename "$file")
                source "$file" 2>/dev/null || true
                echo "Hostname: $hostname"
                echo "IP: ${ip_address:-Unknown}"
                echo "Isolated: ${isolated_at:-Unknown}"
                echo "Reason: ${reason:-Not specified}"
                echo "---"
            fi
        done
    else
        echo "No hosts are currently isolated"
    fi
}

# Function to get isolation status
get_isolation_status() {
    local hostname=$1
    
    if is_isolated "$hostname"; then
        echo "Host $hostname IS ISOLATED"
        cat "$ISOLATION_DIR/$hostname"
    else
        echo "Host $hostname is NOT isolated"
    fi
}

# Command line interface
case "$1" in
    isolate)
        if [[ $# -lt 2 ]]; then
            echo "Usage: $0 isolate <HOSTNAME> [REASON]"
            exit 1
        fi
        isolate_host "$2" "${3:-Security incident response}"
        ;;
    restore)
        if [[ $# -ne 2 ]]; then
            echo "Usage: $0 restore <HOSTNAME>"
            exit 1
        fi
        restore_host "$2"
        ;;
    list)
        list_isolated_hosts
        ;;
    status)
        if [[ $# -ne 2 ]]; then
            echo "Usage: $0 status <HOSTNAME>"
            exit 1
        fi
        get_isolation_status "$2"
        ;;
    *)
        echo "SIEMX Host Isolation Script"
        echo "Usage: $0 {isolate|restore|list|status} [arguments]"
        echo ""
        echo "Commands:"
        echo "  isolate <hostname> [reason]  - Isolate a compromised host"
        echo "  restore <hostname>           - Restore a host to normal network access"
        echo "  list                         - List all isolated hosts"
        echo "  status <hostname>            - Show isolation status for a host"
        echo ""
        echo "Examples:"
        echo "  $0 isolate compromised-server-01 \"Malware infection detected\""
        echo "  $0 restore compromised-server-01"
        echo "  $0 list"
        echo "  $0 status compromised-server-01"
        exit 1
        ;;
esac