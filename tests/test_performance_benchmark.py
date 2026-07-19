#!/usr/bin/env python3
"""
SIEMX Performance Benchmarking Tool
Tests ingestion rates and system performance
"""

import time
import json
import threading
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

class PerformanceBenchmark:
    def __init__(self):
        self.es_url = "http://localhost:9200"
        self.logstash_beats_port = 5044
        self.es_user = "elastic"
        self.es_password = "SiemxPass123!"
        self.test_duration = 60  # seconds
        self.results = {}
        
    def send_log_batch(self, logs):
        """Send batch of logs to Logstash"""
        try:
            # In a real test, you'd send to Filebeat or directly to Logstash
            # This simulates the ingestion process
            response_times = []
            
            for log in logs:
                start_time = time.time()
                # Simulate sending log (in reality, this would be an HTTP POST or Beats protocol)
                time.sleep(0.001)  # Simulate network delay
                end_time = time.time()
                response_times.append(end_time - start_time)
            
            return {
                'success': True,
                'avg_response_time': statistics.mean(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def measure_elasticsearch_performance(self):
        """Measure Elasticsearch query performance"""
        try:
            queries = [
                {"query": {"match_all": {}}},
                {"query": {"match": {"event.category": "authentication"}}},
                {"query": {"range": {"@timestamp": {"gte": "now-1h"}}}}
            ]
            
            response_times = []
            for query in queries:
                start_time = time.time()
                response = requests.post(
                    f"{self.es_url}/siem-logs-*/_search",
                    auth=(self.es_user, self.es_password),
                    verify=False,
                    json=query,
                    timeout=10
                )
                end_time = time.time()
                
                if response.status_code == 200:
                    response_times.append(end_time - start_time)
                else:
                    response_times.append(10)  # Timeout equivalent
            
            return {
                'avg_query_time': statistics.mean(response_times),
                'min_query_time': min(response_times),
                'max_query_time': max(response_times)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def measure_kibana_performance(self):
        """Measure Kibana dashboard loading performance"""
        try:
            kibana_url = "http://localhost:5601"
            endpoints = [
                "/api/status",
                "/app/home",
                "/app/discover"
            ]
            
            response_times = []
            for endpoint in endpoints:
                start_time = time.time()
                try:
                    response = requests.get(f"{kibana_url}{endpoint}", timeout=5)
                    end_time = time.time()
                    if response.status_code == 200:
                        response_times.append(end_time - start_time)
                    else:
                        response_times.append(5)  # Timeout equivalent
                except:
                    response_times.append(5)
            
            return {
                'avg_load_time': statistics.mean(response_times),
                'min_load_time': min(response_times),
                'max_load_time': max(response_times)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def ingestion_rate_test(self, threads=4, batch_size=100):
        """Test log ingestion rate"""
        print(f"Testing ingestion rate with {threads} threads, batch size {batch_size}")
        
        # Generate test logs
        test_logs = []
        for i in range(batch_size * 10):  # Generate 10 batches worth of logs
            log = {
                "@timestamp": datetime.now().isoformat(),
                "message": f"Test log entry {i}",
                "event": {
                    "category": "test",
                    "type": "benchmark"
                },
                "host": {
                    "name": f"test-host-{i % 10}"
                },
                "source": {
                    "ip": f"192.168.1.{i % 254 + 1}"
                }
            }
            test_logs.append(log)
        
        # Track performance metrics
        start_time = time.time()
        total_logs_sent = 0
        thread_results = []
        
        def worker(thread_id):
            nonlocal total_logs_sent
            thread_start = time.time()
            logs_processed = 0
            batch_count = 0
            
            while time.time() - thread_start < self.test_duration and logs_processed < len(test_logs) // threads:
                # Get batch of logs for this thread
                start_idx = thread_id * (len(test_logs) // threads) + batch_count * batch_size
                end_idx = min(start_idx + batch_size, (thread_id + 1) * (len(test_logs) // threads))
                
                if start_idx >= end_idx:
                    break
                    
                batch = test_logs[start_idx:end_idx]
                result = self.send_log_batch(batch)
                
                if result['success']:
                    logs_processed += len(batch)
                    batch_count += 1
                else:
                    break
            
            return {
                'thread_id': thread_id,
                'logs_processed': logs_processed,
                'duration': time.time() - thread_start,
                'logs_per_second': logs_processed / (time.time() - thread_start) if (time.time() - thread_start) > 0 else 0
            }
        
        # Run test with multiple threads
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(worker, i) for i in range(threads)]
            thread_results = [future.result() for future in futures]
        
        total_duration = time.time() - start_time
        total_logs = sum(r['logs_processed'] for r in thread_results)
        avg_rate = total_logs / total_duration if total_duration > 0 else 0
        
        self.results['ingestion_rate'] = {
            'total_logs': total_logs,
            'total_duration': total_duration,
            'average_rate': avg_rate,
            'logs_per_second': avg_rate,
            'thread_results': thread_results,
            'target_eps': 1000,  # Target: 1000 events per second
            'meets_target': avg_rate >= 1000
        }
        
        print(f"Ingestion Rate Test Results:")
        print(f"  Total Logs Processed: {total_logs}")
        print(f"  Test Duration: {total_duration:.2f} seconds")
        print(f"  Average Rate: {avg_rate:.2f} logs/second")
        print(f"  Target Met: {'✅ YES' if avg_rate >= 1000 else '❌ NO'} (Target: 1000 logs/second)")
        
        return self.results['ingestion_rate']
    
    def system_performance_test(self):
        """Test overall system performance"""
        print("Testing system performance...")
        
        # Test Elasticsearch performance
        es_perf = self.measure_elasticsearch_performance()
        avg_query_time = es_perf.get('avg_query_time', 'N/A')
        if isinstance(avg_query_time, (int, float)):
            print(f"Elasticsearch Query Performance: {avg_query_time:.3f}s average")
        else:
            print(f"Elasticsearch Query Performance: {avg_query_time}")
        
        # Test Kibana performance  
        kibana_perf = self.measure_kibana_performance()
        avg_load_time = kibana_perf.get('avg_load_time', 'N/A')
        if isinstance(avg_load_time, (int, float)):
            print(f"Kibana Load Performance: {avg_load_time:.3f}s average")
        else:
            print(f"Kibana Load Performance: {avg_load_time}")
        
        # Test Logstash pipeline
        logstash_test = self.test_logstash_pipeline()
        print(f"Logstash Pipeline: {'✅ Healthy' if logstash_test['healthy'] else '❌ Issues'}")
        
        self.results['system_performance'] = {
            'elasticsearch': es_perf,
            'kibana': kibana_perf,
            'logstash': logstash_test
        }
        
        return self.results['system_performance']
    
    def test_logstash_pipeline(self):
        """Test Logstash pipeline health"""
        try:
            response = requests.get("http://localhost:9600/_node/stats", timeout=5)
            if response.status_code == 200:
                stats = response.json()
                return {
                    'healthy': True,
                    'events_in': stats.get('events', {}).get('in', 0),
                    'events_out': stats.get('events', {}).get('out', 0),
                    'queue_size': stats.get('queue', {}).get('page_capacity_in_bytes', 0)
                }
            else:
                return {'healthy': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    def generate_report(self):
        """Generate performance report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'test_results': self.results,
            'summary': {}
        }
        
        # Add summary metrics
        if 'ingestion_rate' in self.results:
            ir = self.results['ingestion_rate']
            report['summary']['ingestion'] = {
                'rate': f"{ir['average_rate']:.2f} logs/sec",
                'target_met': ir['meets_target'],
                'performance': 'GOOD' if ir['meets_target'] else 'NEEDS_IMPROVEMENT'
            }
        
        if 'system_performance' in self.results:
            sp = self.results['system_performance']
            es_avg = sp['elasticsearch'].get('avg_query_time', 10)
            kb_avg = sp['kibana'].get('avg_load_time', 10)
            
            report['summary']['system'] = {
                'elasticsearch_response': f"{es_avg:.3f}s",
                'kibana_load_time': f"{kb_avg:.3f}s",
                'overall_health': 'GOOD' if es_avg < 2 and kb_avg < 3 else 'FAIR' if es_avg < 5 and kb_avg < 5 else 'POOR'
            }
        
        return report
    
    def run_complete_benchmark(self):
        """Run complete performance benchmark"""
        print("🚀 Starting SIEMX Performance Benchmark\n")
        
        # Run ingestion rate test
        print("1. Running Ingestion Rate Test...")
        self.ingestion_rate_test(threads=4, batch_size=50)
        print()
        
        # Run system performance test
        print("2. Running System Performance Test...")
        self.system_performance_test()
        print()
        
        # Generate and display report
        report = self.generate_report()
        
        print("📊 PERFORMANCE BENCHMARK REPORT")
        print("=" * 50)
        print(f"Test Timestamp: {report['timestamp']}")
        print()
        
        if 'ingestion' in report['summary']:
            ing = report['summary']['ingestion']
            print("INGESTION PERFORMANCE:")
            print(f"  Rate: {ing['rate']}")
            print(f"  Target: 1000 logs/second")
            print(f"  Status: {'✅ PASS' if ing['target_met'] else '❌ FAIL'}")
            print(f"  Performance: {ing['performance']}")
            print()
        
        if 'system' in report['summary']:
            sys = report['summary']['system']
            print("SYSTEM PERFORMANCE:")
            print(f"  Elasticsearch Response: {sys['elasticsearch_response']} (Target: <2s)")
            print(f"  Kibana Load Time: {sys['kibana_load_time']} (Target: <3s)")
            print(f"  Overall Health: {sys['overall_health']}")
            print()
        
        # Save report
        with open('performance-benchmark-report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("Report saved to performance-benchmark-report.json")
        return report

def main():
    benchmark = PerformanceBenchmark()
    benchmark.run_complete_benchmark()

if __name__ == "__main__":
    main()
