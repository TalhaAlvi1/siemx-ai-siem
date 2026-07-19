#!/usr/bin/env python3
"""
SIEMX Log Generation Test
Generates realistic test logs for SIEM testing
"""

import json
import random
import ipaddress
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

class LogGenerator:
    def __init__(self):
        self.windows_event_ids = [4624, 4625, 4672, 4688, 4648, 4720, 4726]
        self.common_ports = [22, 23, 25, 53, 80, 110, 135, 139, 443, 445, 993, 995, 1723, 3389, 5900, 8080]
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        ]
        
    def generate_windows_event(self, event_type="success"):
        """Generate Windows event log"""
        event_id = random.choice(self.windows_event_ids)
        timestamp = datetime.now() - timedelta(minutes=random.randint(0, 1440))
        
        base_event = {
            "@timestamp": timestamp.isoformat(),
            "winlog": {
                "provider_name": "Microsoft-Windows-Security-Auditing",
                "event_id": event_id,
                "level": "Information"
            },
            "host": {
                "name": fake.hostname(),
                "ip": [str(fake.ipv4_private())]
            },
            "tags": ["windows"]
        }
        
        if event_id == 4624:  # Successful logon
            base_event.update({
                "event": {
                    "category": "authentication",
                    "type": "logon_success",
                    "outcome": "success"
                },
                "winlog": {
                    "event_data": {
                        "TargetUserName": fake.user_name(),
                        "IpAddress": str(fake.ipv4_public()),
                        "WorkstationName": fake.hostname()
                    }
                }
            })
        elif event_id == 4625:  # Failed logon
            base_event.update({
                "event": {
                    "category": "authentication", 
                    "type": "logon_failure",
                    "outcome": "failure"
                },
                "winlog": {
                    "event_data": {
                        "TargetUserName": random.choice(["administrator", "admin", "root"] + [fake.user_name() for _ in range(5)]),
                        "IpAddress": str(fake.ipv4_public()),
                        "WorkstationName": fake.hostname()
                    }
                }
            })
        elif event_id == 4688:  # Process creation
            base_event.update({
                "event": {
                    "category": "process",
                    "type": "creation", 
                    "outcome": "info"
                },
                "winlog": {
                    "event_data": {
                        "ProcessName": random.choice(["cmd.exe", "powershell.exe", "net.exe", "at.exe"]),
                        "ProcessId": str(random.randint(1000, 9999))
                    }
                }
            })
            
        return base_event
    
    def generate_linux_auth_log(self):
        """Generate Linux authentication log"""
        timestamp = datetime.now() - timedelta(minutes=random.randint(0, 1440))
        ip = str(fake.ipv4_public())
        
        # Randomly choose success or failure
        if random.random() < 0.8:  # 80% success
            message = f"Accepted publickey for {fake.user_name()} from {ip} port {random.randint(32000, 65000)} ssh2"
            outcome = "success"
            event_type = "login_success"
        else:  # 20% failure
            message = f"Failed password for {random.choice(['invalid_user', 'administrator', 'root', fake.user_name()])} from {ip} port {random.randint(32000, 65000)} ssh2"
            outcome = "failure"
            event_type = "login_failure"
        
        return {
            "@timestamp": timestamp.isoformat(),
            "message": message,
            "system": {
                "syslog": {
                    "program": "sshd"
                }
            },
            "host": {
                "name": fake.hostname()
            },
            "source": {
                "ip": ip
            },
            "event": {
                "category": "authentication",
                "type": event_type,
                "outcome": outcome
            },
            "tags": ["linux"]
        }
    
    def generate_network_log(self):
        """Generate network traffic log"""
        timestamp = datetime.now() - timedelta(minutes=random.randint(0, 1440))
        
        # Randomly choose normal or suspicious traffic
        if random.random() < 0.95:  # 95% normal
            source_ip = str(fake.ipv4_private())
            dest_ip = str(fake.ipv4_private())
            dest_port = random.choice([22, 80, 443, 3389])
            protocol = random.choice(["TCP", "UDP"])
            message = f"{source_ip} > {dest_ip}:{dest_port}"
        else:  # 5% suspicious - port scanning
            source_ip = str(fake.ipv4_public())
            dest_ip = str(fake.ipv4_private())
            dest_port = random.choice(self.common_ports)
            protocol = "TCP"
            message = f"{source_ip} > {dest_ip}:{dest_port}"
        
        return {
            "@timestamp": timestamp.isoformat(),
            "message": message,
            "source": {
                "ip": source_ip
            },
            "destination": {
                "ip": dest_ip,
                "port": dest_port
            },
            "network": {
                "protocol": protocol,
                "bytes": random.randint(64, 1024)
            },
            "event": {
                "category": "network_traffic",
                "type": "connection",
                "outcome": "info"
            },
            "host": {
                "name": fake.hostname()
            },
            "tags": ["network"]
        }
    
    def generate_brute_force_attack(self, count=10):
        """Generate a series of failed login attempts (brute force)"""
        logs = []
        target_ip = str(fake.ipv4_public())
        target_host = fake.hostname()
        username = random.choice(["administrator", "admin", "root"])
        start_time = datetime.now() - timedelta(minutes=5)
        
        for i in range(count):
            timestamp = start_time + timedelta(seconds=i*30)  # 30 seconds apart
            log = {
                "@timestamp": timestamp.isoformat(),
                "message": f"Failed password for {username} from {target_ip} port {random.randint(32000, 65000)} ssh2",
                "system": {
                    "syslog": {
                        "program": "sshd"
                    }
                },
                "host": {
                    "name": target_host
                },
                "source": {
                    "ip": target_ip
                },
                "event": {
                    "category": "authentication",
                    "type": "login_failure",
                    "outcome": "failure"
                },
                "tags": ["linux", "brute_force_simulation"]
            }
            logs.append(log)
            
        return logs

def main():
    """Generate test logs and save to file"""
    generator = LogGenerator()
    logs = []
    
    print("Generating test logs...")
    
    # Generate normal logs
    for _ in range(50):
        logs.append(generator.generate_windows_event())
        logs.append(generator.generate_linux_auth_log())
        logs.append(generator.generate_network_log())
    
    # Generate brute force attack scenario
    logs.extend(generator.generate_brute_force_attack(15))
    
    # Generate some additional suspicious activity
    for _ in range(5):
        # Port scanning simulation
        scanner_ip = str(fake.ipv4_public())
        target_host = fake.hostname()
        for port in random.sample(generator.common_ports, 12):  # Scan 12 different ports
            timestamp = datetime.now() - timedelta(minutes=random.randint(0, 10))
            log = {
                "@timestamp": timestamp.isoformat(),
                "message": f"{scanner_ip} > {fake.ipv4_private()}:{port}",
                "source": {
                    "ip": scanner_ip
                },
                "destination": {
                    "ip": str(fake.ipv4_private()),
                    "port": port
                },
                "network": {
                    "protocol": "TCP"
                },
                "event": {
                    "category": "network_traffic",
                    "type": "connection",
                    "outcome": "info"
                },
                "host": {
                    "name": target_host
                },
                "tags": ["network", "port_scan_simulation"]
            }
            logs.append(log)
    
    # Sort logs by timestamp
    logs.sort(key=lambda x: x["@timestamp"])
    
    # Save to file
    output_file = "sample-test-logs.json"
    with open(output_file, 'w') as f:
        json.dump(logs, f, indent=2)
    
    print(f"Generated {len(logs)} test logs")
    print(f"Saved to {output_file}")
    
    # Print summary
    event_types = {}
    for log in logs:
        category = log.get('event', {}).get('category', 'unknown')
        event_types[category] = event_types.get(category, 0) + 1
    
    print("\nLog Distribution:")
    for category, count in event_types.items():
        print(f"  {category}: {count}")

if __name__ == "__main__":
    main()