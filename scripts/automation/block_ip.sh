#!/bin/bash
#
# SIEMX IP Blocking Script
# Automatically blocks malicious IPs using iptables

# Configuration
LOG_FILE="/var/log/siemx/ip-block.log"
BLOCK_LIST="/etc/siemx/blocked-ips.txt"
TEMP_BLOCK_DURATION="1h"  # Temporary block duration
PERM_THRESHOLD=10         # Number of offenses for permanent block

# Create necessary directories and files
mkdir -p /etc/siemx
touch "$BLOCK_LIST"
touch "$LOG_FILE"

# Function to log actions
log_action() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to check if IP is already blocked
is_blocked() {
    local ip=$1
    iptables -C INPUT -s "$ip" -j DROP 2>/dev/null
    return $?
}

# Function to temporarily block an IP
temp_block_ip() {
    local ip=$1
    local reason=${2:-"Suspicious activity"}
    
    if ! is_blocked "$ip"; then
        iptables -A INPUT -s "$ip" -j DROP
        log_action "TEMPORARILY BLOCKED $ip - $reason"
        echo "$ip $(date +%s) temp $reason" >> "$BLOCK_LIST"
        echo "Blocked IP $ip temporarily: $reason"
    else
        echo "IP $ip is already blocked"
    fi
}

# Function to permanently block an IP
perm_block_ip() {
    local ip=$1
    local reason=${2:-"Multiple security violations"}
    
    if ! is_blocked "$ip"; then
        iptables -A INPUT -s "$ip" -j DROP
        log_action "PERMANENTLY BLOCKED $ip - $reason"
        echo "$ip $(date +%s) perm $reason" >> "$BLOCK_LIST"
        echo "Permanently blocked IP $ip: $reason"
    else
        echo "IP $ip is already blocked"
    fi
}

# Function to unblock an IP
unblock_ip() {
    local ip=$1
    
    if is_blocked "$ip"; then
        iptables -D INPUT -s "$ip" -j DROP
        sed -i "/^$ip /d" "$BLOCK_LIST"
        log_action "UNBLOCKED $ip"
        echo "Unblocked IP $ip"
    else
        echo "IP $ip is not currently blocked"
    fi
}

# Function to check block expiration
check_expiration() {
    local current_time=$(date +%s)
    local expiration_time=$((current_time - 3600))  # 1 hour ago
    
    while IFS= read -r line; do
        if [[ $line =~ ^([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\ ([0-9]+)\ temp ]]; then
            local ip="${BASH_REMATCH[1]}"
            local block_time="${BASH_REMATCH[2]}"
            
            if [[ $block_time -lt $expiration_time ]]; then
                unblock_ip "$ip"
            fi
        fi
    done < "$BLOCK_LIST"
}

# Function to get offense count for an IP
get_offense_count() {
    local ip=$1
    grep "^$ip " "$BLOCK_LIST" | wc -l
}

# Main function to handle IP blocking
block_malicious_ip() {
    local ip=$1
    local reason=${2:-"Security violation"}
    local offense_count
    
    # Validate IP format
    if ! [[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "Invalid IP address: $ip"
        return 1
    fi
    
    # Check offense count
    offense_count=$(get_offense_count "$ip")
    
    if [[ $offense_count -ge $((PERM_THRESHOLD - 1)) ]]; then
        perm_block_ip "$ip" "$reason (Offense #$((offense_count + 1)))"
    else
        temp_block_ip "$ip" "$reason (Offense #$((offense_count + 1)))"
    fi
}

# Function to list blocked IPs
list_blocked_ips() {
    echo "Currently Blocked IPs:"
    echo "====================="
    iptables -L INPUT -v -n | grep DROP | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+' | sort -u
    
    echo -e "\nBlock Records:"
    echo "============="
    cat "$BLOCK_LIST"
}

# Function to cleanup expired temporary blocks
cleanup_expired_blocks() {
    echo "Cleaning up expired temporary blocks..."
    check_expiration
    echo "Cleanup completed"
}

# Command line interface
case "$1" in
    block)
        if [[ $# -lt 2 ]]; then
            echo "Usage: $0 block <IP_ADDRESS> [REASON]"
            exit 1
        fi
        block_malicious_ip "$2" "${3:-Manual block}"
        ;;
    unblock)
        if [[ $# -ne 2 ]]; then
            echo "Usage: $0 unblock <IP_ADDRESS>"
            exit 1
        fi
        unblock_ip "$2"
        ;;
    list)
        list_blocked_ips
        ;;
    cleanup)
        cleanup_expired_blocks
        ;;
    *)
        echo "SIEMX IP Blocking Script"
        echo "Usage: $0 {block|unblock|list|cleanup} [arguments]"
        echo ""
        echo "Commands:"
        echo "  block <IP> [reason]   - Block an IP address"
        echo "  unblock <IP>          - Unblock an IP address"
        echo "  list                  - List all blocked IPs"
        echo "  cleanup               - Remove expired temporary blocks"
        echo ""
        echo "Examples:"
        echo "  $0 block 192.168.1.100 \"Brute force attack\""
        echo "  $0 unblock 192.168.1.100"
        echo "  $0 list"
        echo "  $0 cleanup"
        exit 1
        ;;
esac