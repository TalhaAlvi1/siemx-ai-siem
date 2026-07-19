#!/usr/bin/env python3
"""
Test script for SIEMX Anomaly Detection Service
"""

import requests
import json
import time
from datetime import datetime

def test_health_check():
    """Test the health check endpoint"""
    try:
        response = requests.get('http://localhost:8080/health', timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_training():
    """Test model training"""
    try:
        response = requests.post('http://localhost:8080/train', timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Model training successful")
                return True
            else:
                print(f"❌ Model training failed: {result.get('message')}")
                return False
        else:
            print(f"❌ Training endpoint error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Training test error: {e}")
        return False

def test_detection():
    """Test anomaly detection"""
    # Sample log data for testing
    sample_logs = [
        {
            "@timestamp": datetime.now().isoformat(),
            "source.ip": "192.168.1.100",
            "event.outcome": "success",
            "user.name": "john.doe",
            "log.level": "info"
        },
        {
            "@timestamp": datetime.now().isoformat(),
            "source.ip": "192.168.1.101",
            "event.outcome": "failure",
            "user.name": "invalid.user",
            "log.level": "error"
        }
    ]
    
    try:
        response = requests.post(
            'http://localhost:8080/detect',
            json={"logs": sample_logs},
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Detection test passed - Found {result.get('count', 0)} anomalies")
            return True
        else:
            print(f"❌ Detection test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Detection test error: {e}")
        return False

def test_scoring():
    """Test individual scoring"""
    sample_features = {
        "hour_of_day": 3,
        "source_ip_count": 50,
        "event_count": 1000,
        "failed_logins": 50,
        "unique_users": 5
    }
    
    try:
        response = requests.post(
            'http://localhost:8080/score',
            json={"features": sample_features},
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Scoring test passed - Anomaly: {result.get('is_anomaly')}, Score: {result.get('anomaly_score'):.3f}")
            return True
        else:
            print(f"❌ Scoring test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Scoring test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running SIEMX Anomaly Detection Tests\n")
    
    tests = [
        ("Health Check", test_health_check),
        ("Model Training", test_training),
        ("Anomaly Detection", test_detection),
        ("Individual Scoring", test_scoring)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed")
        return False

if __name__ == "__main__":
    main()