#!/usr/bin/env python3
"""
SIEMX Performance Test Suite
Tests the performance and scalability of the SIEMX system
"""

import os
import time
import json
import requests
import threading
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import argparse

class SIEMXPerformanceTester:
    def __init__(self):
        self.es_host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
        self.es_port = int(os.getenv('ELASTICSEARCH_PORT', 9200))
        self.es_user = os.getenv('ELASTICSEARCH_USER', 'elastic')
        self.es_password = os.getenv('ELASTICSEARCH_PASSWORD', 'SiemxPass123!')
        self.test_index = 'siemx-performance-test'
        
        self.results = {
            'throughput': [],
            'latency': [],
            'errors': 0,
            'successes': 0
        }

    def generate_test_log(self, log_id):
        """Generate a realistic test log"""
        return {
            "@timestamp": datetime.utcnow().isoformat(),
            "message": f"Performance test log #{log_id}",
            "event": {
                "category": "authentication",
                "type": "login_success" if log_id % 2 == 0 else "login_failure",
                "outcome": "success" if log_id % 2 == 0 else "failure"
            },
            "source": {
                "ip": f"192.168.1.{log_id % 254 + 1}",
                "port": 54321
            },
            "user": {
                "name": f"user_{log_id % 1000}"
            },
            "host": {
                "name": f"server_{log_id % 10}"
            },
            "network": {
                "bytes": 1024 + (log_id % 1000)
            }
        }

    def send_single_log(self, log_data):
        """Send a single log to Elasticsearch and measure latency"""
        es_url = f"http://{self.es_host}:{self.es_port}"
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{es_url}/{self.test_index}/_doc",
                auth=(self.es_user, self.es_password),
                json=log_data,
                timeout=10
            )
            
            end_time = time.time()
            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            
            if response.status_code in [200, 201]:
                self.results['successes'] += 1
                self.results['latency'].append(latency)
                return True, latency
            else:
                self.results['errors'] += 1
                return False, latency
                
        except Exception as e:
            self.results['errors'] += 1
            return False, 0

    def test_throughput(self, num_logs=1000, concurrency=10):
        """Test throughput by sending multiple logs concurrently"""
        print(f"\\n🚀 Testing throughput: {num_logs} logs with {concurrency} concurrent threads")
        
        logs = [self.generate_test_log(i) for i in range(num_logs)]
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(self.send_single_log, log) for log in logs]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        eps = num_logs / total_time  # Events per second
        avg_latency = statistics.mean(self.results['latency']) if self.results['latency'] else 0
        p95_latency = statistics.quantiles(self.results['latency'], n=20)[-1] if len(self.results['latency']) > 1 else 0
        
        print(f"✅ Throughput test completed:")
        print(f"   • Total logs sent: {num_logs}")
        print(f"   • Time taken: {total_time:.2f}s")
        print(f"   • Average throughput: {eps:.2f} EPS")
        print(f"   • Average latency: {avg_latency:.2f}ms")
        print(f"   • 95th percentile latency: {p95_latency:.2f}ms")
        print(f"   • Successful logs: {self.results['successes']}")
        print(f"   • Failed logs: {self.results['errors']}")
        print(f"   • Success rate: {(self.results['successes']/num_logs)*100:.2f}%")
        
        return {
            'total_logs': num_logs,
            'time_taken': total_time,
            'eps': eps,
            'avg_latency_ms': avg_latency,
            'p95_latency_ms': p95_latency,
            'success_rate': (self.results['successes']/num_logs)*100,
            'errors': self.results['errors']
        }

    def test_scalability(self, log_counts=[100, 500, 1000, 2000]):
        """Test scalability with increasing log volumes"""
        print("\\n📈 Testing scalability with different log volumes...")
        
        scalability_results = {}
        
        for count in log_counts:
            # Reset results for each test
            self.results = {
                'throughput': [],
                'latency': [],
                'errors': 0,
                'successes': 0
            }
            
            result = self.test_throughput(num_logs=count, concurrency=min(count, 50))
            scalability_results[count] = result
            
            # Small delay between tests
            time.sleep(5)
        
        return scalability_results

    def test_concurrent_load(self, num_threads_list=[1, 5, 10, 20, 50]):
        """Test performance under different concurrency levels"""
        print("\\n⚡ Testing performance under different concurrency levels...")
        
        concurrency_results = {}
        
        for num_threads in num_threads_list:
            # Reset results for each test
            self.results = {
                'throughput': [],
                'latency': [],
                'errors': 0,
                'successes': 0
            }
            
            result = self.test_throughput(num_logs=500, concurrency=num_threads)
            concurrency_results[num_threads] = result
            
            # Small delay between tests
            time.sleep(10)
        
        return concurrency_results

    def generate_performance_report(self, results):
        """Generate a comprehensive performance report"""
        print("\\n📊 PERFORMANCE REPORT")
        print("=" * 80)
        
        if 'scalability' in results:
            print("\\n📈 SCALABILITY RESULTS:")
            print("Logs | EPS    | Avg Latency | 95% Latency | Success Rate")
            print("-" * 65)
            for count, result in results['scalability'].items():
                print(f"{count:4d} | {result['eps']:6.2f} | {result['avg_latency_ms']:9.2f}ms | "
                      f"{result['p95_latency_ms']:10.2f}ms | {result['success_rate']:8.2f}%")
        
        if 'concurrency' in results:
            print("\\n⚡ CONCURRENCY RESULTS:")
            print("Threads | EPS    | Avg Latency | 95% Latency | Success Rate")
            print("-" * 67)
            for threads, result in results['concurrency'].items():
                print(f"{threads:5d} | {result['eps']:6.2f} | {result['avg_latency_ms']:9.2f}ms | "
                      f"{result['p95_latency_ms']:10.2f}ms | {result['success_rate']:8.2f}%")
        
        print("\\n🎯 PERFORMANCE TARGETS:")
        print("   • Throughput: ≥ 1000 EPS")
        print("   • Latency: ≤ 2000ms average, ≤ 5000ms 95th percentile")
        print("   • Success Rate: ≥ 95%")
        print("   • Scalability: Maintain performance as load increases")
        
        # Overall assessment
        print("\\n🏆 OVERALL ASSESSMENT:")
        if 'concurrency' in results:
            max_eps = max(r['eps'] for r in results['concurrency'].values())
            avg_lat = min(r['avg_latency_ms'] for r in results['concurrency'].values())
            max_success = max(r['success_rate'] for r in results['concurrency'].values())
            
            print(f"   • Peak throughput: {max_eps:.2f} EPS")
            print(f"   • Best latency: {avg_lat:.2f}ms average")
            print(f"   • Highest success rate: {max_success:.2f}%")
            
            if max_eps >= 1000 and avg_lat <= 2000 and max_success >= 95:
                print("   ✅ System meets performance targets!")
            else:
                print("   ⚠️  System may need optimization to meet targets.")

def main():
    parser = argparse.ArgumentParser(description='SIEMX Performance Test Suite')
    parser.add_argument('--basic', action='store_true', help='Run basic performance test')
    parser.add_argument('--scalability', action='store_true', help='Run scalability test')
    parser.add_argument('--concurrency', action='store_true', help='Run concurrency test')
    parser.add_argument('--all', action='store_true', help='Run all performance tests')
    parser.add_argument('--logs', type=int, default=1000, help='Number of logs for basic test')
    parser.add_argument('--threads', type=int, default=10, help='Number of concurrent threads')
    
    args = parser.parse_args()
    
    tester = SIEMXPerformanceTester()
    results = {}
    
    print("🚀 Starting SIEMX Performance Tests")
    print("=" * 80)
    
    if args.basic or args.all:
        print("\\n🧪 BASIC PERFORMANCE TEST")
        tester.results = {
            'throughput': [],
            'latency': [],
            'errors': 0,
            'successes': 0
        }
        basic_result = tester.test_throughput(num_logs=args.logs, concurrency=args.threads)
        results['basic'] = basic_result
    
    if args.scalability or args.all:
        print("\\n🧪 SCALABILITY TEST")
        tester.results = {
            'throughput': [],
            'latency': [],
            'errors': 0,
            'successes': 0
        }
        scalability_results = tester.test_scalability()
        results['scalability'] = scalability_results
    
    if args.concurrency or args.all:
        print("\\n🧪 CONCURRENCY TEST")
        tester.results = {
            'throughput': [],
            'latency': [],
            'errors': 0,
            'successes': 0
        }
        concurrency_results = tester.test_concurrent_load()
        results['concurrency'] = concurrency_results
    
    # Generate report
    tester.generate_performance_report(results)
    
    print("\\n" + "=" * 80)
    print("Performance testing completed!")

if __name__ == "__main__":
    main()
