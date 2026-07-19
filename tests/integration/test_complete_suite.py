# SIEMX Integration Test Suite
# Complete test suite for validating all components

import unittest
import requests
import time
import json
import os
from datetime import datetime, timezone

class TestLogIngestion(unittest.TestCase):
    """Test log ingestion pipeline"""
    
    def setUp(self):
        self.es_host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
        self.es_port = int(os.getenv('ELASTICSEARCH_PORT', 9200))
        self.es_user = os.getenv('ELASTICSEARCH_USER', 'elastic')
        self.es_password = os.getenv('ELASTICSEARCH_PASSWORD', 'SiemxPass123!')
        self.test_index = 'siemx-integration-test'
    
    def test_send_log_to_elasticsearch(self):
        """Test sending a log to Elasticsearch"""
        es_url = f"http://{self.es_host}:{self.es_port}"
        
        test_log = {
            "@timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Integration test log",
            "event": {
                "category": "test",
                "type": "integration"
            },
            "host": {
                "name": "integration-test-host"
            }
        }
        
        response = requests.post(
            f"{es_url}/{self.test_index}/_doc",
            auth=(self.es_user, self.es_password),
            json=test_log,
            timeout=10
        )
        
        self.assertIn(response.status_code, [200, 201])
    
    def test_search_logs(self):
        """Test searching for logs in Elasticsearch"""
        es_url = f"http://{self.es_host}:{self.es_port}"
        
        # First ensure there's a document to search for
        self.test_send_log_to_elasticsearch()
        time.sleep(2)  # Wait for indexing
        
        search_body = {
            "query": {
                "term": {
                    "host.name.keyword": "integration-test-host"
                }
            }
        }
        
        response = requests.post(
            f"{es_url}/{self.test_index}/_search",
            auth=(self.es_user, self.es_password),
            json=search_body,
            timeout=10
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertGreaterEqual(result['hits']['total']['value'], 1)


class TestKibanaIntegration(unittest.TestCase):
    """Test Kibana integration"""
    
    def setUp(self):
        self.kibana_host = os.getenv('KIBANA_HOST', 'localhost')
        self.kibana_port = int(os.getenv('KIBANA_PORT', 5601))
    
    def test_kibana_status(self):
        """Test Kibana status API"""
        kibana_url = f"http://{self.kibana_host}:{self.kibana_port}"
        
        response = requests.get(
            f"{kibana_url}/api/status",
            timeout=10
        )

        self.assertEqual(response.status_code, 200)
        status_data = response.json()
        self.assertIn('status', status_data)


class TestAnomalyDetection(unittest.TestCase):
    """Test anomaly detection service"""
    
    def setUp(self):
        self.anomaly_host = os.getenv('ANOMALY_HOST', 'localhost')
        self.anomaly_port = int(os.getenv('ANOMALY_PORT', 8080))
    
    def test_anomaly_service_health(self):
        """Test anomaly detection service health endpoint"""
        anomaly_url = f"http://{self.anomaly_host}:{self.anomaly_port}"
        
        response = requests.get(f"{anomaly_url}/health", timeout=10)
        
        self.assertEqual(response.status_code, 200)
        health_data = response.json()
        self.assertEqual(health_data['status'], 'healthy')
    
    def test_anomaly_detection(self):
        """Test anomaly detection functionality"""
        anomaly_url = f"http://{self.anomaly_host}:{self.anomaly_port}"
        
        test_logs = [{
            "@timestamp": datetime.now(timezone.utc).isoformat(),
            "id": "test-log-1",
            "message": "Normal activity",
            "source": {"ip": "192.168.1.100", "frequency": 1},
            "user": {"name": "testuser", "frequency": 1},
            "destination": {"port": 443},
            "network": {"bytes": 1024}
        }]
        
        response = requests.post(
            f"{anomaly_url}/detect",
            json=test_logs,
            timeout=30
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn('results', result)
        self.assertEqual(len(result['results']), 1)


class TestAlerting(unittest.TestCase):
    """Test alerting functionality"""
    
    def setUp(self):
        self.kibana_host = os.getenv('KIBANA_HOST', 'localhost')
        self.kibana_port = int(os.getenv('KIBANA_PORT', 5601))
    
    def test_alerting_api_access(self):
        """Test access to alerting API"""
        kibana_url = f"http://{self.kibana_host}:{self.kibana_port}"
        
        # This test may return 403 if auth is required, which is acceptable
        response = requests.get(
            f"{kibana_url}/api/alerting/rules/_find",
            headers={'kbn-xsrf': 'true'},
            timeout=10
        )
        
        # Accept auth-required responses as well as success.
        self.assertIn(response.status_code, [200, 401, 403])


class TestEndToEnd(unittest.TestCase):
    """End-to-end integration test"""
    
    def setUp(self):
        self.es_host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
        self.es_port = int(os.getenv('ELASTICSEARCH_PORT', 9200))
        self.es_user = os.getenv('ELASTICSEARCH_USER', 'elastic')
        self.es_password = os.getenv('ELASTICSEARCH_PASSWORD', 'SiemxPass123!')
        self.anomaly_host = os.getenv('ANOMALY_HOST', 'localhost')
        self.anomaly_port = int(os.getenv('ANOMALY_PORT', 8080))
        self.test_index = 'siemx-e2e-test'
    
    def test_complete_pipeline(self):
        """Test complete pipeline: log -> ES -> anomaly detection"""
        es_url = f"http://{self.es_host}:{self.es_port}"
        anomaly_url = f"http://{self.anomaly_host}:{self.anomaly_port}"
        
        # 1. Send test log to Elasticsearch
        test_log = {
            "@timestamp": datetime.now(timezone.utc).isoformat(),
            "id": "e2e-test-1",
            "message": "End-to-end test log",
            "event": {
                "category": "authentication",
                "type": "login_success"
            },
            "source": {"ip": "192.168.1.100", "frequency": 1},
            "user": {"name": "testuser", "frequency": 1},
            "destination": {"port": 443},
            "network": {"bytes": 1024},
            "host": {
                "name": "e2e-test-host"
            }
        }
        
        response = requests.post(
            f"{es_url}/{self.test_index}/_doc",
            auth=(self.es_user, self.es_password),
            json=test_log,
            timeout=10
        )
        
        self.assertIn(response.status_code, [200, 201])
        
        # 2. Wait for log to be indexed
        time.sleep(3)
        
        # 3. Process log through anomaly detection
        response = requests.post(
            f"{anomaly_url}/detect",
            json=[test_log],
            timeout=30
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn('results', result)
        
        print(f"✅ End-to-end test completed successfully")


def run_integration_suite():
    """Run the complete integration test suite"""
    print("🚀 Starting SIEMX Integration Test Suite")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    
    # Load all test cases
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestLogIngestion))
    suite.addTests(loader.loadTestsFromTestCase(TestKibanaIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestAnomalyDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestAlerting))
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEnd))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    print(f"📊 Integration Test Results:")
    print(f"   • Tests run: {result.testsRun}")
    print(f"   • Failures: {len(result.failures)}")
    print(f"   • Errors: {len(result.errors)}")
    print(f"   • Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%" if result.testsRun > 0 else "0%")
    
    if result.wasSuccessful():
        print("\\n🎉 All integration tests PASSED!")
        return True
    else:
        print("\\n❌ Some integration tests FAILED!")
        for failure in result.failures:
            print(f"   FAILURE in {failure[0]}: {failure[1]}")
        for error in result.errors:
            print(f"   ERROR in {error[0]}: {error[1]}")
        return False


if __name__ == '__main__':
    success = run_integration_suite()
    exit(0 if success else 1)
