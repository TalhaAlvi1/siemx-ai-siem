#!/usr/bin/env python3
"""
SIEMX Simulation (Without Docker)
This script simulates the core functionality of the SIEMX system
without requiring Docker or the full ELK stack installation.
"""

import os
import sys
import json
import time
import threading
from datetime import datetime, timedelta
from collections import defaultdict
import random
import argparse

class SIEMXSimulator:
    def __init__(self):
        self.running = False
        self.logs = []
        self.alerts = []
        self.metrics = {
            'total_events': 0,
            'security_events': 0,
            'normal_events': 0,
            'anomalies_detected': 0
        }
        self.threat_intel = {
            'known_bad_ips': ['192.168.100.10', '10.0.0.50', '203.0.113.45'],
            'suspicious_ports': [22, 445, 3389, 1433, 3306]
        }
        
    def generate_sample_logs(self, count=50):
        """Generate sample security logs for demonstration"""
        print(f"📊 Generating {count} sample logs...")
        
        base_time = datetime.now() - timedelta(minutes=count//2)
        
        for i in range(count):
            timestamp = base_time + timedelta(seconds=i*2)
            
            # Randomly choose log type
            log_type = random.choice([
                'authentication_success', 'authentication_failure',
                'network_connection', 'process_creation', 'file_access'
            ])
            
            log = {
                '@timestamp': timestamp.isoformat(),
                'event': {
                    'category': '',
                    'type': '',
                    'outcome': ''
                },
                'source': {
                    'ip': f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}",
                    'port': random.randint(1024, 65535)
                },
                'destination': {
                    'ip': f"10.0.{random.randint(0, 255)}.{random.randint(1, 255)}",
                    'port': random.choice([80, 443, 22, 3389, 1433, 3306, 5432])
                },
                'user': {
                    'name': random.choice(['admin', 'user123', 'service_acct', 'guest', 'testuser'])
                },
                'host': {
                    'name': f"server-{random.randint(1, 20)}",
                    'os': random.choice(['Windows', 'Linux', 'macOS'])
                }
            }
            
            # Set event-specific fields
            if 'authentication' in log_type:
                log['event']['category'] = 'authentication'
                log['event']['type'] = 'login_' + ('success' if 'success' in log_type else 'failure')
                log['event']['outcome'] = 'success' if 'success' in log_type else 'failure'
                
            elif log_type == 'network_connection':
                log['event']['category'] = 'network'
                log['event']['type'] = 'connection'
                log['event']['outcome'] = random.choice(['allowed', 'blocked'])
                
            elif log_type == 'process_creation':
                log['event']['category'] = 'process'
                log['event']['type'] = 'creation'
                log['event']['outcome'] = 'success'
                log['process'] = {
                    'name': random.choice(['powershell.exe', 'cmd.exe', 'bash', 'python', 'ssh']),
                    'pid': random.randint(1000, 99999)
                }
            
            self.logs.append(log)
            self.metrics['total_events'] += 1
            
            # Update metrics
            if log['event']['category'] in ['authentication', 'network', 'process']:
                self.metrics['security_events'] += 1
            else:
                self.metrics['normal_events'] += 1
        
        print(f"✅ Generated {len(self.logs)} sample logs")
        return self.logs

    def detect_threats(self):
        """Detect potential threats in the logs"""
        print("🔍 Analyzing logs for potential threats...")
        
        threat_count = 0
        for log in self.logs:
            is_threat = False
            
            # Check for known bad IPs
            if log['source']['ip'] in self.threat_intel['known_bad_ips']:
                is_threat = True
                threat_type = "Known Bad IP"
            
            # Check for suspicious ports
            if log['destination']['port'] in self.threat_intel['suspicious_ports']:
                is_threat = True
                threat_type = "Suspicious Port Access"
            
            # Check for multiple failed authentications
            if (log['event']['type'] == 'login_failure' and 
                log['event']['outcome'] == 'failure'):
                is_threat = True
                threat_type = "Multiple Authentication Failures"
            
            if is_threat:
                alert = {
                    'timestamp': log['@timestamp'],
                    'type': 'threat_detected',
                    'severity': 'high',
                    'description': f"Potential threat detected: {threat_type}",
                    'source_ip': log['source']['ip'],
                    'destination_ip': log['destination']['ip'],
                    'related_log': log
                }
                self.alerts.append(alert)
                threat_count += 1
        
        print(f"⚠️  Detected {threat_count} potential threats")
        return threat_count

    def run_real_time_simulation(self, duration=30):
        """Run a real-time simulation for the specified duration in seconds"""
        print(f"🚀 Starting real-time simulation for {duration} seconds...")
        
        self.running = True
        start_time = time.time()
        
        while time.time() - start_time < duration and self.running:
            # Generate new logs periodically
            if len(self.logs) % 10 == 0:
                new_log = self.generate_sample_logs(1)[0]
                print(f"📥 New event: {new_log['event']['category']} - {new_log['event']['type']}")
            
            # Occasionally detect threats
            if len(self.logs) % 15 == 0:
                self.detect_threats()
            
            time.sleep(1)
            
            # Show periodic status
            if len(self.logs) % 5 == 0:
                print(f"📈 Status: {len(self.logs)} events processed, {len(self.alerts)} alerts generated")
        
        self.running = False
        print("⏹️  Simulation completed")
    
    def print_summary(self):
        """Print a summary of the simulation"""
        print("\n" + "="*60)
        print("📊 SIEMX SIMULATION SUMMARY")
        print("="*60)
        print(f"Total Events Processed: {self.metrics['total_events']}")
        print(f"Security Events: {self.metrics['security_events']}")
        print(f"Normal Events: {self.metrics['normal_events']}")
        print(f"Anomalies Detected: {self.metrics['anomalies_detected']}")
        print(f"Alerts Generated: {len(self.alerts)}")
        print("="*60)
        
        if self.alerts:
            print("\n🚨 RECENT ALERTS:")
            for alert in self.alerts[-5:]:  # Show last 5 alerts
                print(f"  • {alert['description']} ({alert['severity']})")
                print(f"    Source: {alert['source_ip']} → Destination: {alert['destination_ip']}")
        
        print("\n✅ SIEMX Simulation completed successfully!")

    def export_logs(self, filename='simulated_logs.json'):
        """Export generated logs to a file"""
        with open(filename, 'w') as f:
            json.dump(self.logs, f, indent=2)
        print(f"💾 Exported {len(self.logs)} logs to {filename}")

def main():
    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    
    parser = argparse.ArgumentParser(description='SIEMX Simulator (No Docker Required)')
    parser.add_argument('--simulate', action='store_true', help='Run real-time simulation')
    parser.add_argument('--duration', type=int, default=30, help='Simulation duration in seconds')
    parser.add_argument('--generate', type=int, default=50, help='Number of initial logs to generate')
    parser.add_argument('--export', action='store_true', help='Export logs to file')
    
    args = parser.parse_args()
    
    print("🚀 Starting SIEMX Simulator (No Docker Required)")
    print("="*60)
    
    simulator = SIEMXSimulator()
    
    # Generate initial logs
    simulator.generate_sample_logs(args.generate)
    
    # Detect initial threats
    simulator.detect_threats()
    
    if args.simulate:
        # Run real-time simulation
        simulator.run_real_time_simulation(args.duration)
    else:
        # Just show initial analysis
        print(f"🔍 Initial analysis completed. Generated {len(simulator.logs)} logs.")
        print(f"⚠️  Found {len(simulator.alerts)} potential threats.")
    
    # Print summary
    simulator.print_summary()
    
    if args.export:
        simulator.export_logs()
    
    print("\n🎯 SIEMX Simulator provides a demonstration of:")
    print("  - Log collection and processing")
    print("  - Threat detection algorithms")
    print("  - Alert generation and correlation")
    print("  - Real-time monitoring capabilities")
    print("  - Security event analysis")

if __name__ == "__main__":
    main()