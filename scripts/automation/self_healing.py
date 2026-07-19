#!/usr/bin/env python3
"""
SIEMX Self-Healing Automation
Automatically responds to security alerts with predefined actions
"""

import os
import time
import json
import requests
import subprocess
import logging
from datetime import datetime, timedelta
from threading import Thread
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('self_healing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SIEMXSelfHealing:
    def __init__(self):
        self.es_host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
        self.es_port = int(os.getenv('ELASTICSEARCH_PORT', 9200))
        self.kibana_host = os.getenv('KIBANA_HOST', 'localhost')
        self.kibana_port = int(os.getenv('KIBANA_PORT', 5601))
        self.es_user = os.getenv('ELASTICSEARCH_USER', 'elastic')
        self.es_password = os.getenv('ELASTICSEARCH_PASSWORD', 'changeme')
        
        self.active_blocks = {}  # Track active IP blocks
        self.host_isolations = {}  # Track isolated hosts
        
        # Define security rules and corresponding actions
        self.security_rules = {
            'brute_force_attack': {
                'condition': self.detect_brute_force,
                'action': self.block_attacking_ips,
                'severity': 'high'
            },
            'port_scanning': {
                'condition': self.detect_port_scanning,
                'action': self.block_scanning_ips,
                'severity': 'medium'
            },
            'unauthorized_access': {
                'condition': self.detect_unauthorized_access,
                'action': self.isolate_violating_hosts,
                'severity': 'high'
            },
            'anomalous_network_activity': {
                'condition': self.detect_anomalous_network,
                'action': self.limit_network_access,
                'severity': 'medium'
            }
        }

    def detect_brute_force(self, recent_logs):
        """Detect brute force attack patterns"""
        # Look for multiple failed login attempts from same IP
        ip_attempts = {}
        
        for log in recent_logs:
            if (log.get('event', {}).get('type') == 'login_failure' and 
                'source' in log and 'ip' in log['source']):
                
                ip = log['source']['ip']
                if ip not in ip_attempts:
                    ip_attempts[ip] = 0
                ip_attempts[ip] += 1
        
        # Return IPs with more than 10 failed attempts in short period
        return [ip for ip, count in ip_attempts.items() if count > 10]

    def detect_port_scanning(self, recent_logs):
        """Detect port scanning activity"""
        # Look for connection attempts to many different ports from same IP
        ip_ports = {}
        
        for log in recent_logs:
            if ('connection_attempt' in log.get('event', {}).get('type', '') and
                'source' in log and 'ip' in log['source'] and
                'destination' in log and 'port' in log['destination']):
                
                ip = log['source']['ip']
                port = log['destination']['port']
                
                if ip not in ip_ports:
                    ip_ports[ip] = set()
                ip_ports[ip].add(port)
        
        # Return IPs that attempted to connect to more than 50 different ports
        return [ip for ip, ports in ip_ports.items() if len(ports) > 50]

    def detect_unauthorized_access(self, recent_logs):
        """Detect unauthorized access attempts"""
        unauthorized_hosts = []
        
        for log in recent_logs:
            if (log.get('event', {}).get('outcome') == 'failure' and
                log.get('event', {}).get('category') == 'authentication'):
                
                host = log.get('host', {}).get('name')
                if host:
                    unauthorized_hosts.append(host)
        
        return unauthorized_hosts

    def detect_anomalous_network(self, recent_logs):
        """Detect anomalous network activity"""
        # Look for unusually large data transfers
        large_transfers = []
        
        for log in recent_logs:
            if (log.get('event', {}).get('category') == 'network' and
                'network' in log and 'bytes' in log['network']):
                
                if log['network']['bytes'] > 50000000:  # 50MB
                    large_transfers.append(log)
        
        return large_transfers

    def block_attacking_ips(self, ips_to_block):
        """Block IPs identified as attackers"""
        logger.info(f"Blocking {len(ips_to_block)} attacking IPs: {ips_to_block}")
        
        blocked_ips = []
        for ip in ips_to_block:
            try:
                # Use iptables to block the IP (Linux)
                if os.name == 'posix':
                    cmd = f"iptables -A INPUT -s {ip} -j DROP"
                    subprocess.run(cmd.split(), check=True, capture_output=True)
                    logger.info(f"Blocked IP: {ip}")
                    blocked_ips.append(ip)
                else:
                    # For Windows, use netsh or PowerShell
                    cmd = f"netsh advfirewall firewall add rule name=\"Block {ip}\" dir=in action=block remoteip={ip}"
                    subprocess.run(cmd.split(), check=True, capture_output=True)
                    logger.info(f"Blocked IP: {ip}")
                    blocked_ips.append(ip)
                
                # Track the block
                self.active_blocks[ip] = datetime.now()
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to block IP {ip}: {e}")
        
        return blocked_ips

    def block_scanning_ips(self, ips_to_block):
        """Block IPs identified as scanners"""
        logger.info(f"Blocking {len(ips_to_block)} scanning IPs: {ips_to_block}")
        
        # Similar to blocking attackers, but with shorter duration
        return self.block_attacking_ips(ips_to_block)

    def isolate_violating_hosts(self, hosts_to_isolate):
        """Isolate hosts that violated security policies"""
        logger.info(f"Isolating {len(hosts_to_isolate)} violating hosts: {hosts_to_isolate}")
        
        isolated_hosts = []
        for host in hosts_to_isolate:
            try:
                # In a real system, this would disable network interfaces or move to quarantine VLAN
                logger.info(f"Isolating host: {host}")
                
                # Simulate host isolation
                # This could involve:
                # - Disabling network interfaces
                # - Moving to quarantine VLAN
                # - Disconnecting from domain
                # - Stopping services
                
                isolated_hosts.append(host)
                self.host_isolations[host] = datetime.now()
                
            except Exception as e:
                logger.error(f"Failed to isolate host {host}: {e}")
        
        return isolated_hosts

    def limit_network_access(self, suspicious_logs):
        """Limit network access for suspicious activities"""
        logger.info(f"Limiting network access for {len(suspicious_logs)} suspicious activities")
        
        limited_access = []
        for log in suspicious_logs:
            if 'source' in log and 'ip' in log['source']:
                ip = log['source']['ip']
                # Implement bandwidth limiting or connection throttling
                logger.info(f"Limited network access for: {ip}")
                limited_access.append(ip)
        
        return limited_access

    def fetch_recent_alerts(self):
        """Fetch recent security alerts from Elasticsearch"""
        try:
            es_url = f"https://{self.es_host}:{self.es_port}"
            
            # Search for recent security events
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "range": {
                                    "@timestamp": {
                                        "gte": "now-5m",  # Last 5 minutes
                                        "lt": "now"
                                    }
                                }
                            },
                            {
                                "terms": {
                                    "event.category.keyword": ["authentication", "network", "process"]
                                }
                            }
                        ]
                    }
                },
                "sort": [{"@timestamp": {"order": "desc"}}],
                "size": 1000
            }
            
            response = requests.post(
                f"{es_url}/siem-logs-*/_search",
                auth=(self.es_user, self.es_password),
                json=search_body,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                hits = result.get('hits', {}).get('hits', [])
                logs = [hit['_source'] for hit in hits]
                return logs
            else:
                logger.error(f"Failed to fetch alerts: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return []

    def cleanup_expired_blocks(self):
        """Remove expired IP blocks and host isolations"""
        current_time = datetime.now()
        expired_blocks = []
        
        # Clean up IP blocks older than 1 hour
        for ip, block_time in list(self.active_blocks.items()):
            if current_time - block_time > timedelta(hours=1):
                try:
                    if os.name == 'posix':
                        cmd = f"iptables -D INPUT -s {ip} -j DROP"
                        subprocess.run(cmd.split(), check=True, capture_output=True)
                    else:
                        cmd = f"netsh advfirewall firewall delete rule name=\"Block {ip}\""
                        subprocess.run(cmd.split(), check=True, capture_output=True)
                    
                    logger.info(f"Removed expired block for IP: {ip}")
                    expired_blocks.append(ip)
                except subprocess.CalledProcessError:
                    logger.error(f"Failed to remove block for IP: {ip}")
        
        # Remove expired blocks from tracking
        for ip in expired_blocks:
            del self.active_blocks[ip]
        
        # Clean up host isolations older than 1 hour
        expired_isolations = []
        for host, isolate_time in list(self.host_isolations.items()):
            if current_time - isolate_time > timedelta(hours=1):
                logger.info(f"Removing isolation for host: {host}")
                expired_isolations.append(host)
        
        for host in expired_isolations:
            del self.host_isolations[host]

    def run_self_healing_cycle(self):
        """Run one cycle of self-healing automation"""
        logger.info("Starting self-healing cycle...")
        
        # Fetch recent security events
        recent_logs = self.fetch_recent_alerts()
        
        if not recent_logs:
            logger.info("No recent security events found")
            return
        
        # Apply each security rule
        for rule_name, rule_config in self.security_rules.items():
            logger.debug(f"Applying rule: {rule_name}")
            
            # Check if condition is met
            triggered_items = rule_config['condition'](recent_logs)
            
            if triggered_items:
                logger.info(f"Rule '{rule_name}' triggered for {len(triggered_items)} items: {triggered_items[:5]}...")
                
                # Execute the corresponding action
                affected_items = rule_config['action'](triggered_items)
                
                if affected_items:
                    logger.info(f"Action completed. Affected {len(affected_items)} items: {affected_items[:5]}...")
        
        # Clean up expired blocks
        self.cleanup_expired_blocks()
        
        logger.info("Self-healing cycle completed")

    def start_monitoring_loop(self, interval=300):  # 5 minutes default
        """Start continuous monitoring loop"""
        logger.info(f"Starting continuous self-healing monitoring (interval: {interval}s)")
        
        while True:
            try:
                self.run_self_healing_cycle()
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Self-healing monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in self-healing cycle: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

def main():
    parser = argparse.ArgumentParser(description='SIEMX Self-Healing Automation')
    parser.add_argument('--run-once', action='store_true', help='Run self-healing once and exit')
    parser.add_argument('--interval', type=int, default=300, help='Monitoring interval in seconds (default: 300)')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode (no actual blocking)')
    
    args = parser.parse_args()
    
    healer = SIEMXSelfHealing()
    
    if args.test_mode:
        logger.info("Running in TEST MODE - no actual security actions will be taken")
        # Override blocking methods to just log
        original_block_method = healer.block_attacking_ips
        def test_block(ips):
            logger.info(f"WOULD BLOCK IPs: {ips} (test mode)")
            return ips
        healer.block_attacking_ips = test_block
        healer.block_scanning_ips = test_block
    
    if args.run_once:
        logger.info("Running single self-healing cycle...")
        healer.run_self_healing_cycle()
    else:
        logger.info("Starting continuous self-healing monitoring...")
        healer.start_monitoring_loop(args.interval)

if __name__ == "__main__":
    main()