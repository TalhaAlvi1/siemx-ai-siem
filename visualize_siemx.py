#!/usr/bin/env python3
"""
SIEMX Project Visualization and Demonstration
Shows the running SIEMX system with visualizations
"""

import requests
import json
import time
from datetime import datetime, timedelta
import random
import sys

def print_header(text):
    """Print formatted header"""
    print("\\n" + "="*60)
    print(f" {text}")
    print("="*60)

def test_anomaly_service():
    """Test the anomaly detection service"""
    print("1. Testing Anomaly Detection Service...")
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Service Health: {health_data['status']}")
            print(f"   Timestamp: {health_data['timestamp']}")
            return True
        else:
            print(f"❌ Service returned status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Service not responding - please start anomaly detection service")
        print("   Run: cd anomaly-detection && python anomaly_detector.py")
        return False
    except Exception as e:
        print(f"❌ Error testing service: {e}")
        return False

def test_detection_api():
    """Test the anomaly detection API"""
    print("\\n2. Testing Anomaly Detection API...")
    
    # Sample test data
    test_logs = [
        {
            "@timestamp": "2026-02-03T10:00:00Z",
            "id": "test-log-1",
            "source": {"ip": "192.168.1.100", "frequency": 1},
            "user": {"name": "admin", "frequency": 1},
            "destination": {"port": 443},
            "network": {"bytes": 1024}
        },
        {
            "@timestamp": "2026-02-03T10:01:00Z",
            "id": "test-log-2",
            "source": {"ip": "10.0.0.50", "frequency": 50},
            "user": {"name": "admin", "frequency": 1},
            "destination": {"port": 22},
            "network": {"bytes": 1000000}
        },
        {
            "@timestamp": "2026-02-03T10:02:00Z",
            "id": "test-log-3",
            "source": {"ip": "172.16.0.25", "frequency": 1},
            "user": {"name": "user123", "frequency": 1},
            "destination": {"port": 80},
            "network": {"bytes": 512}
        }
    ]
    
    try:
        response = requests.post(
            "http://localhost:8080/detect",
            json=test_logs,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Detection Results:")
            print(f"   Total Processed: {result['total_processed']}")
            print(f"   Anomalies Detected: {result['anomalies_detected']}")
            
            print("\\n   Detailed Results:")
            for res in result['results']:
                status = "ANOMALY" if res['is_anomaly'] else "NORMAL"
                status_color = "\\033[91m" if res['is_anomaly'] else "\\033[92m"
                reset_color = "\\033[0m"
                print(f"   - Log ID: {res['log_id']}")
                print(f"     Anomaly Score: {res['score']:.4f}")
                print(f"     Status: {status_color}{status}{reset_color}")
                print(f"     Severity: {res['severity']}")
                print()
            
            return True
        else:
            print(f"❌ API returned status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing detection API: {e}")
        return False

def generate_sample_logs():
    """Generate sample security logs for visualization"""
    print("3. Generating Sample Security Logs...")
    
    logs = []
    start_time = datetime(2026, 2, 3, 8, 0, 0)
    
    # Generate normal events (80%)
    for i in range(80):
        timestamp = start_time + timedelta(minutes=i*2)
        logs.append({
            "timestamp": timestamp,
            "event_type": "Normal Login",
            "ip": f"192.168.1.{random.randint(10, 250)}",
            "user": f"user{random.randint(1000, 9999)}",
            "status": "Success",
            "risk_score": round(random.uniform(0.0, 0.2), 3),
            "category": "Normal"
        })
    
    # Generate suspicious events (20%)
    for i in range(20):
        timestamp = start_time + timedelta(minutes=random.randint(0, 120))
        suspicious_types = ["Failed Login", "Port Scan", "Unusual Activity"]
        event_type = random.choice(suspicious_types)
        
        # Different IP ranges for suspicious activity
        if i < 10:
            ip = f"10.0.0.{random.randint(100, 200)}"
        else:
            ip = f"192.168.100.{random.randint(10, 100)}"
        
        logs.append({
            "timestamp": timestamp,
            "event_type": event_type,
            "ip": ip,
            "user": f"attacker{random.randint(1000, 9999)}",
            "status": "Failed",
            "risk_score": round(random.uniform(0.7, 1.0), 3),
            "category": "Suspicious"
        })
    
    print(f"✅ Generated {len(logs)} sample logs")
    print(f"   - Normal Events: {len([l for l in logs if l['category'] == 'Normal'])}")
    print(f"   - Suspicious Events: {len([l for l in logs if l['category'] == 'Suspicious'])}")
    print(f"   - High-Risk Events: {len([l for l in logs if l['risk_score'] > 0.7])}")
    
    return logs

def create_timeline_visualization(logs):
    """Create timeline visualization"""
    print("\\n📊 Timeline Visualization (Last 2 Hours)")
    print("-" * 50)
    
    start_time = datetime(2026, 2, 3, 8, 0, 0)
    
    # Group by 30-minute intervals
    intervals = {}
    for log in logs:
        minutes_diff = int((log['timestamp'] - start_time).total_seconds() / 60)
        interval = minutes_diff // 30
        if interval not in intervals:
            intervals[interval] = {"normal": 0, "suspicious": 0, "total": 0}
        intervals[interval]["total"] += 1
        if log['category'] == 'Normal':
            intervals[interval]["normal"] += 1
        else:
            intervals[interval]["suspicious"] += 1
    
    # Display timeline
    for interval in sorted(intervals.keys()):
        interval_start = start_time + timedelta(minutes=interval * 30)
        interval_end = interval_start + timedelta(minutes=30)
        
        data = intervals[interval]
        total_events = data['total']
        
        # Create visual bar
        bar_length = min(40, total_events)
        normal_bar = "=" * int((data['normal'] / total_events) * bar_length) if total_events > 0 else ""
        suspicious_bar = "!" * int((data['suspicious'] / total_events) * bar_length) if total_events > 0 else ""
        
        print(f"{interval_start.strftime('%H:%M')}-{interval_end.strftime('%H:%M')}: "
              f"[{normal_bar}{suspicious_bar}] {total_events} events ({data['normal']}/{data['suspicious']})")
    
    print("\\nLegend: = Normal Events, ! Suspicious Events")

def create_risk_distribution(logs):
    """Create risk distribution visualization"""
    print("\\n📊 Risk Score Distribution")
    print("-" * 30)
    
    risk_groups = {"Low Risk": 0, "Medium Risk": 0, "High Risk": 0}
    
    for log in logs:
        if log['risk_score'] < 0.3:
            risk_groups["Low Risk"] += 1
        elif log['risk_score'] < 0.7:
            risk_groups["Medium Risk"] += 1
        else:
            risk_groups["High Risk"] += 1
    
    total = len(logs)
    for category, count in risk_groups.items():
        percentage = (count / total) * 100 if total > 0 else 0
        bar_length = int((count / total) * 30) if total > 0 else 0
        bar = "█" * bar_length
        
        # Color coding (using ANSI codes)
        if category == "Low Risk":
            color = "\\033[92m"  # Green
        elif category == "Medium Risk":
            color = "\\033[93m"  # Yellow
        else:
            color = "\\033[91m"  # Red
        
        reset = "\\033[0m"
        print(f"{color}{category}: {bar} {count} ({percentage:.1f}%){reset}")

def create_summary_visualization(logs):
    """Create summary visualization"""
    print("\\n🎯 SIEMX Activity Summary")
    print("=" * 40)
    
    # Time range
    timestamps = [log['timestamp'] for log in logs]
    start_time = min(timestamps)
    end_time = max(timestamps)
    
    print(f"Time Period: {start_time.strftime('%m/%d %H:%M')} to {end_time.strftime('%H:%M')}")
    print(f"Total Events: {len(logs)}")
    
    # Event categories
    normal_count = len([l for l in logs if l['category'] == 'Normal'])
    suspicious_count = len([l for l in logs if l['category'] == 'Suspicious'])
    print(f"Normal Events: {normal_count}")
    print(f"Suspicious Events: {suspicious_count}")
    
    # Risk statistics
    high_risk = len([l for l in logs if l['risk_score'] > 0.7])
    avg_risk = sum(log['risk_score'] for log in logs) / len(logs) if logs else 0
    print(f"High-Risk Events: {high_risk}")
    print(f"Average Risk Score: {avg_risk:.3f}")
    
    # Top suspicious IPs
    suspicious_ips = [log['ip'] for log in logs if log['category'] == 'Suspicious']
    if suspicious_ips:
        ip_counts = {}
        for ip in suspicious_ips:
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
        top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        print("\\nTop Suspicious IPs:")
        for ip, count in top_ips:
            print(f"  {ip}: {count} events")

def main():
    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    
    """Main function to run the SIEMX visualization"""
    print_header("SIEMX PROJECT VISUALIZATION DEMO")
    
    print("🚀 Demonstrating SIEMX Project Capabilities:")
    print("   • Anomaly Detection Service")
    print("   • Security Event Analysis")
    print("   • Real-time Visualization")
    print("   • Threat Intelligence")
    
    # Test services
    service_ok = test_anomaly_service()
    if service_ok:
        test_detection_api()
    
    # Generate and visualize data
    logs = generate_sample_logs()
    create_timeline_visualization(logs)
    create_risk_distribution(logs)
    create_summary_visualization(logs)
    
    print_header("SIEMX VISUALIZATION COMPLETE")
    
    if service_ok:
        print("✅ SIEMX Project Status: RUNNING")
        print("   • Anomaly Detection Service: ACTIVE")
        print("   • API Endpoints: Available on port 8080")
        print("   • Visualization: Complete")
    else:
        print("⚠️  SIEMX Project Status: PARTIAL")
        print("   • Anomaly Detection Service: NOT RUNNING")
        print("   • Visualization: Available (simulated)")
        print("   • To start service: cd anomaly-detection && python anomaly_detector.py")
    
    print("\\n🔧 Access Points:")
    print("   • Anomaly Detection API: http://localhost:8080")
    print("   • Health Check: http://localhost:8080/health")
    print("   • Detection Endpoint: http://localhost:8080/detect")
    
    print("\\n📊 For full ELK Stack visualization:")
    print("   Install Elasticsearch, Logstash, and Kibana")
    print("   See MANUAL_INSTALLATION.md for detailed instructions")

if __name__ == "__main__":
    main()