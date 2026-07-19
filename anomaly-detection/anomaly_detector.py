#!/usr/bin/env python3
"""
SIEMX Anomaly Detection Service
Uses Isolation Forest algorithm to detect anomalous security events
"""

import os
import json
import time
import numpy as np
from flask import Flask, request, jsonify
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pandas as pd
import requests
from datetime import datetime, timedelta
from threading import Thread
import joblib

app = Flask(__name__)

class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_columns = [
            'hour', 'day_of_week', 'source_ip_freq', 
            'user_freq', 'dest_port', 'bytes_transferred',
            'request_rate'
        ]
        
        # Elasticsearch connection details
        self.es_host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
        self.es_port = int(os.getenv('ELASTICSEARCH_PORT', 9200))
        self.es_user = os.getenv('ELASTICSEARCH_USERNAME', os.getenv('ELASTICSEARCH_USER', 'elastic'))
        self.es_password = os.getenv('ELASTICSEARCH_PASSWORD', 'changeme')
        
        # Initialize with sample training data
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the model with sample training data"""
        # Create sample training data (this would normally come from historical logs)
        sample_data = np.array([
            [8, 1, 1, 1, 443, 1024, 1],
            [9, 1, 1, 1, 80, 512, 1],
            [10, 1, 1, 1, 22, 256, 1],
            [14, 2, 2, 1, 443, 2048, 2],
            [15, 2, 1, 2, 80, 1024, 1],
            [22, 5, 1, 1, 443, 512, 1],
            [23, 5, 3, 1, 22, 128, 3],
            [0, 6, 1, 1, 443, 256, 1],
            [1, 6, 1, 1, 80, 512, 1],
            [2, 6, 1, 1, 22, 256, 1],
        ])
        
        self.scaler.fit(sample_data)
        scaled_data = self.scaler.transform(sample_data)
        self.model.fit(scaled_data)
        self.is_trained = True
        
        print("✅ Anomaly detection model initialized")

    def extract_features(self, log_entry):
        """Extract numerical features from log entry for anomaly detection"""
        timestamp = datetime.fromisoformat(log_entry.get('@timestamp', datetime.now().isoformat()).replace('Z', '+00:00'))
        
        # Extract temporal features
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        
        # Extract frequency-based features (would normally come from aggregation)
        source_ip_freq = log_entry.get('source', {}).get('frequency', 1)
        user_freq = log_entry.get('user', {}).get('frequency', 1)
        
        # Extract other features
        dest_port = log_entry.get('destination', {}).get('port', 0)
        bytes_transferred = log_entry.get('network', {}).get('bytes', 0)
        
        # Calculate request rate (simplified)
        request_rate = 1  # Would normally be calculated from recent logs
        
        return np.array([[hour, day_of_week, source_ip_freq, user_freq, dest_port, bytes_transferred, request_rate]])

    def predict_anomaly(self, log_entry):
        """Predict if a log entry is anomalous"""
        if not self.is_trained:
            return 0.0, False  # No anomaly (default)
        
        features = self.extract_features(log_entry)
        scaled_features = self.scaler.transform(features)
        
        # Predict anomaly (-1 for anomaly, 1 for normal)
        prediction = self.model.predict(scaled_features)[0]
        score = self.model.decision_function(scaled_features)[0]
        
        is_anomaly = prediction == -1
        normalized_score = float(score)  # Convert to native Python float
        
        return normalized_score, is_anomaly

    def score_features(self, features):
        """Score a precomputed feature vector."""
        if not self.is_trained:
            return 0.0, False

        scaled_features = self.scaler.transform([features])
        prediction = self.model.predict(scaled_features)[0]
        score = self.model.decision_function(scaled_features)[0]
        return float(score), prediction == -1

    def retrain_model(self, training_data):
        """Retrain the model with new data"""
        if len(training_data) > 0:
            df = pd.DataFrame(training_data)
            feature_matrix = df[self.feature_columns].fillna(0).values
            
            scaled_data = self.scaler.fit_transform(feature_matrix)
            self.model.fit(scaled_data)
            self.is_trained = True
            
            print(f"✅ Model retrained with {len(training_data)} samples")

detector = AnomalyDetector()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_trained': detector.is_trained,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/detect', methods=['POST'])
def detect_anomaly():
    """Detect anomalies in incoming log data"""
    try:
        log_data = request.json
        
        if isinstance(log_data, dict):
            log_data = [log_data]
        elif not isinstance(log_data, list):
            return jsonify({'error': 'Invalid input format'}), 400
        
        results = []
        for log_entry in log_data:
            score, is_anomaly = detector.predict_anomaly(log_entry)
            results.append({
                'log_id': log_entry.get('id', 'unknown'),
                'score': float(score),
                'anomaly_score': float(score),
                'is_anomaly': bool(is_anomaly),
                'severity': 'high' if is_anomaly else 'normal'
            })
        
        return jsonify({
            'results': results,
            'total_processed': len(results),
            'anomalies_detected': sum(1 for r in results if r['is_anomaly'])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/score', methods=['POST'])
def score_features():
    """Score a single feature payload."""
    try:
        payload = request.json or {}
        features = payload.get('features')
        if not isinstance(features, dict):
            return jsonify({'error': 'features object is required'}), 400

        ordered_features = [
            float(features.get('hour_of_day', 0)),
            float(features.get('day_of_week', 0)),
            float(features.get('source_ip_count', 0)),
            float(features.get('unique_users', 0)),
            float(features.get('dest_port', 0)),
            float(features.get('bytes_transferred', 0)),
            float(features.get('request_rate', 0)),
        ]
        score, is_anomaly = detector.score_features(ordered_features)
        return jsonify({
            'score': score,
            'anomaly_score': score,
            'is_anomaly': bool(is_anomaly)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/train', methods=['POST'])
def train_model():
    """Retrain the model with new data"""
    try:
        training_data = request.json
        
        if isinstance(training_data, dict):
            training_data = [training_data]
        
        detector.retrain_model(training_data)
        
        return jsonify({
            'success': True,
            'status': 'success',
            'message': f'Model retrained with {len(training_data)} samples'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/batch_detect', methods=['POST'])
def batch_detect():
    """Detect anomalies in batch of logs"""
    try:
        logs = request.json
        
        if not isinstance(logs, list):
            return jsonify({'error': 'Input must be a list of logs'}), 400
        
        results = []
        anomalies = []
        
        for log_entry in logs:
            score, is_anomaly = detector.predict_anomaly(log_entry)
            
            result = {
                'log_id': log_entry.get('id', 'unknown'),
                'timestamp': log_entry.get('@timestamp'),
                'score': float(score),
                'anomaly_score': float(score),
                'is_anomaly': bool(is_anomaly),
                'severity': 'high' if is_anomaly else 'normal'
            }
            
            results.append(result)
            
            if is_anomaly:
                anomalies.append(result)
        
        return jsonify({
            'results': results,
            'total_processed': len(results),
            'anomalies_detected': len(anomalies),
            'anomalies': anomalies
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def fetch_recent_logs():
    """Fetch recent logs from Elasticsearch for continuous learning"""
    try:
        es_url = f"http://{detector.es_host}:{detector.es_port}"
        
        # Search for recent logs
        search_body = {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": "now-1h",
                        "lt": "now"
                    }
                }
            },
            "size": 1000,
            "_source": ["@timestamp", "event.category", "source.ip", "destination.ip", "user.name", "network.bytes"]
        }
        
        response = requests.post(
            f"{es_url}/siem-logs-*/_search",
            auth=(detector.es_user, detector.es_password),
            json=search_body,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            hits = result.get('hits', {}).get('hits', [])
            
            # Process logs for feature extraction
            processed_logs = []
            for hit in hits:
                log = hit.get('_source', {})
                # Extract features here would be more complex in production
                processed_logs.append(log)
            
            return processed_logs
        else:
            print(f"Failed to fetch logs: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"Error fetching logs: {e}")
        return []

def continuous_learning():
    """Background thread for continuous model improvement"""
    while True:
        try:
            # Fetch recent logs
            recent_logs = fetch_recent_logs()
            
            if recent_logs:
                print(f"🔄 Updating model with {len(recent_logs)} recent logs")
                detector.retrain_model(recent_logs)
            
            # Sleep for 10 minutes before next update
            time.sleep(600)
            
        except Exception as e:
            print(f"Error in continuous learning: {e}")
            time.sleep(300)  # Wait 5 minutes before retrying

if __name__ == '__main__':
    # Start continuous learning in background thread
    learning_thread = Thread(target=continuous_learning, daemon=True)
    learning_thread.start()
    
    # Start Flask app
    port = int(os.getenv('PORT', 8080))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Starting SIEMX Anomaly Detection Service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug) 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
sample_data = np.array([[8, 1, 1, 1, 443, 1024, 1]]) 
scaler.fit(sample_data) 
scaled_data = scaler.transform(sample_data) 
model.fit(scaled_data) 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        log_data = request.json 
        if isinstance(log_data, dict): 
            log_data = [log_data] 
        elif not isinstance(log_data, list): 
            return jsonify({'error': 'Invalid input format'}), 400 
        results = [] 
        for log_entry in log_data: 
            score = 0.0 
            is_anomaly = False 
            results.append({ 
                'log_id': log_entry.get('id', 'unknown'), 
                'score': score, 
                'is_anomaly': is_anomaly, 
                'severity': 'normal' 
            }) 
        return jsonify({ 
            'results': results, 
            'total_processed': len(results), 
            'anomalies_detected': sum(1 for r in results if r['is_anomaly']) 
        }) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        data = request.json 
        # Placeholder for anomaly detection logic 
        # In a real implementation, this would analyze the data 
        result = {'is_anomaly': False, 'score': 0.0, 'severity': 'normal'} 
        return jsonify(result) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
sample_data = np.array([[8, 1, 1, 1, 443, 1024, 1]]) 
scaler.fit(sample_data) 
scaled_data = scaler.transform(sample_data) 
model.fit(scaled_data) 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        log_data = request.json 
        if isinstance(log_data, dict): 
            log_data = [log_data] 
        elif not isinstance(log_data, list): 
            return jsonify({'error': 'Invalid input format'}), 400 
        results = [] 
        for log_entry in log_data: 
            score = 0.0 
            is_anomaly = False 
            results.append({ 
                'log_id': log_entry.get('id', 'unknown'), 
                'score': score, 
                'is_anomaly': is_anomaly, 
                'severity': 'normal' 
            }) 
        return jsonify({ 
            'results': results, 
            'total_processed': len(results), 
            'anomalies_detected': sum(1 for r in results if r['is_anomaly']) 
        }) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        data = request.json 
        # Placeholder for anomaly detection logic 
        # In a real implementation, this would analyze the data 
        result = {'is_anomaly': False, 'score': 0.0, 'severity': 'normal'} 
        return jsonify(result) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        data = request.json 
        # Placeholder for anomaly detection logic 
        # In a real implementation, this would analyze the data 
        result = {'is_anomaly': False, 'score': 0.0, 'severity': 'normal'} 
        return jsonify(result) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
sample_data = np.array([[8, 1, 1, 1, 443, 1024, 1]]) 
scaler.fit(sample_data) 
scaled_data = scaler.transform(sample_data) 
model.fit(scaled_data) 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        log_data = request.json 
        if isinstance(log_data, dict): 
            log_data = [log_data] 
        elif not isinstance(log_data, list): 
            return jsonify({'error': 'Invalid input format'}), 400 
        results = [] 
        for log_entry in log_data: 
            score = 0.0 
            is_anomaly = False 
            results.append({ 
                'log_id': log_entry.get('id', 'unknown'), 
                'score': score, 
                'is_anomaly': is_anomaly, 
                'severity': 'normal' 
            }) 
        return jsonify({ 
            'results': results, 
            'total_processed': len(results), 
            'anomalies_detected': sum(1 for r in results if r['is_anomaly']) 
        }) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
sample_data = np.array([[8, 1, 1, 1, 443, 1024, 1]]) 
scaler.fit(sample_data) 
scaled_data = scaler.transform(sample_data) 
model.fit(scaled_data) 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        log_data = request.json 
        if isinstance(log_data, dict): 
            log_data = [log_data] 
        elif not isinstance(log_data, list): 
            return jsonify({'error': 'Invalid input format'}), 400 
        results = [] 
        for log_entry in log_data: 
            score = 0.0 
            is_anomaly = False 
            results.append({ 
                'log_id': log_entry.get('id', 'unknown'), 
                'score': score, 
                'is_anomaly': is_anomaly, 
                'severity': 'normal' 
            }) 
        return jsonify({ 
            'results': results, 
            'total_processed': len(results), 
            'anomalies_detected': sum(1 for r in results if r['is_anomaly']) 
        }) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
sample_data = np.array([[8, 1, 1, 1, 443, 1024, 1]]) 
scaler.fit(sample_data) 
scaled_data = scaler.transform(sample_data) 
model.fit(scaled_data) 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        log_data = request.json 
        if isinstance(log_data, dict): 
            log_data = [log_data] 
        elif not isinstance(log_data, list): 
            return jsonify({'error': 'Invalid input format'}), 400 
        results = [] 
        for log_entry in log_data: 
            score = 0.0 
            is_anomaly = False 
            results.append({ 
                'log_id': log_entry.get('id', 'unknown'), 
                'score': score, 
                'is_anomaly': is_anomaly, 
                'severity': 'normal' 
            }) 
        return jsonify({ 
            'results': results, 
            'total_processed': len(results), 
            'anomalies_detected': sum(1 for r in results if r['is_anomaly']) 
        }) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
sample_data = np.array([[8, 1, 1, 1, 443, 1024, 1]]) 
scaler.fit(sample_data) 
scaled_data = scaler.transform(sample_data) 
model.fit(scaled_data) 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        log_data = request.json 
        if isinstance(log_data, dict): 
            log_data = [log_data] 
        elif not isinstance(log_data, list): 
            return jsonify({'error': 'Invalid input format'}), 400 
        results = [] 
        for log_entry in log_data: 
            score = 0.0 
            is_anomaly = False 
            results.append({ 
                'log_id': log_entry.get('id', 'unknown'), 
                'score': score, 
                'is_anomaly': is_anomaly, 
                'severity': 'normal' 
            }) 
        return jsonify({ 
            'results': results, 
            'total_processed': len(results), 
            'anomalies_detected': sum(1 for r in results if r['is_anomaly']) 
        }) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
sample_data = np.array([[8, 1, 1, 1, 443, 1024, 1]]) 
scaler.fit(sample_data) 
scaled_data = scaler.transform(sample_data) 
model.fit(scaled_data) 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        log_data = request.json 
        if isinstance(log_data, dict): 
            log_data = [log_data] 
        elif not isinstance(log_data, list): 
            return jsonify({'error': 'Invalid input format'}), 400 
        results = [] 
        for log_entry in log_data: 
            score = 0.0 
            is_anomaly = False 
            results.append({ 
                'log_id': log_entry.get('id', 'unknown'), 
                'score': score, 
                'is_anomaly': is_anomaly, 
                'severity': 'normal' 
            }) 
        return jsonify({ 
            'results': results, 
            'total_processed': len(results), 
            'anomalies_detected': sum(1 for r in results if r['is_anomaly']) 
        }) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        data = request.json 
        # Placeholder for anomaly detection logic 
        # In a real implementation, this would analyze the data 
        result = {'is_anomaly': False, 'score': 0.0, 'severity': 'normal'} 
        return jsonify(result) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
sample_data = np.array([[8, 1, 1, 1, 443, 1024, 1]]) 
scaler.fit(sample_data) 
scaled_data = scaler.transform(sample_data) 
model.fit(scaled_data) 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        log_data = request.json 
        if isinstance(log_data, dict): 
            log_data = [log_data] 
        elif not isinstance(log_data, list): 
            return jsonify({'error': 'Invalid input format'}), 400 
        results = [] 
        for log_entry in log_data: 
            score = 0.0 
            is_anomaly = False 
            results.append({ 
                'log_id': log_entry.get('id', 'unknown'), 
                'score': score, 
                'is_anomaly': is_anomaly, 
                'severity': 'normal' 
            }) 
        return jsonify({ 
            'results': results, 
            'total_processed': len(results), 
            'anomalies_detected': sum(1 for r in results if r['is_anomaly']) 
        }) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
sample_data = np.array([[8, 1, 1, 1, 443, 1024, 1]]) 
scaler.fit(sample_data) 
scaled_data = scaler.transform(sample_data) 
model.fit(scaled_data) 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        log_data = request.json 
        if isinstance(log_data, dict): 
            log_data = [log_data] 
        elif not isinstance(log_data, list): 
            return jsonify({'error': 'Invalid input format'}), 400 
        results = [] 
        for log_entry in log_data: 
            score = 0.0 
            is_anomaly = False 
            results.append({ 
                'log_id': log_entry.get('id', 'unknown'), 
                'score': score, 
                'is_anomaly': is_anomaly, 
                'severity': 'normal' 
            }) 
        return jsonify({ 
            'results': results, 
            'total_processed': len(results), 
            'anomalies_detected': sum(1 for r in results if r['is_anomaly']) 
        }) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        data = request.json 
        # Placeholder for anomaly detection logic 
        # In a real implementation, this would analyze the data 
        result = {'is_anomaly': False, 'score': 0.0, 'severity': 'normal'} 
        return jsonify(result) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
sample_data = np.array([[8, 1, 1, 1, 443, 1024, 1]]) 
scaler.fit(sample_data) 
scaled_data = scaler.transform(sample_data) 
model.fit(scaled_data) 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        log_data = request.json 
        if isinstance(log_data, dict): 
            log_data = [log_data] 
        elif not isinstance(log_data, list): 
            return jsonify({'error': 'Invalid input format'}), 400 
        results = [] 
        for log_entry in log_data: 
            score = 0.0 
            is_anomaly = False 
            results.append({ 
                'log_id': log_entry.get('id', 'unknown'), 
                'score': score, 
                'is_anomaly': is_anomaly, 
                'severity': 'normal' 
            }) 
        return jsonify({ 
            'results': results, 
            'total_processed': len(results), 
            'anomalies_detected': sum(1 for r in results if r['is_anomaly']) 
        }) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
sample_data = np.array([[8, 1, 1, 1, 443, 1024, 1]]) 
scaler.fit(sample_data) 
scaled_data = scaler.transform(sample_data) 
model.fit(scaled_data) 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        log_data = request.json 
        if isinstance(log_data, dict): 
            log_data = [log_data] 
        elif not isinstance(log_data, list): 
            return jsonify({'error': 'Invalid input format'}), 400 
        results = [] 
        for log_entry in log_data: 
            score = 0.0 
            is_anomaly = False 
            results.append({ 
                'log_id': log_entry.get('id', 'unknown'), 
                'score': score, 
                'is_anomaly': is_anomaly, 
                'severity': 'normal' 
            }) 
        return jsonify({ 
            'results': results, 
            'total_processed': len(results), 
            'anomalies_detected': sum(1 for r in results if r['is_anomaly']) 
        }) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
sample_data = np.array([[8, 1, 1, 1, 443, 1024, 1]]) 
scaler.fit(sample_data) 
scaled_data = scaler.transform(sample_data) 
model.fit(scaled_data) 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        log_data = request.json 
        if isinstance(log_data, dict): 
            log_data = [log_data] 
        elif not isinstance(log_data, list): 
            return jsonify({'error': 'Invalid input format'}), 400 
        results = [] 
        for log_entry in log_data: 
            score = 0.0 
            is_anomaly = False 
            results.append({ 
                'log_id': log_entry.get('id', 'unknown'), 
                'score': score, 
                'is_anomaly': is_anomaly, 
                'severity': 'normal' 
            }) 
        return jsonify({ 
            'results': results, 
            'total_processed': len(results), 
            'anomalies_detected': sum(1 for r in results if r['is_anomaly']) 
        }) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
sample_data = np.array([[8, 1, 1, 1, 443, 1024, 1]]) 
scaler.fit(sample_data) 
scaled_data = scaler.transform(sample_data) 
model.fit(scaled_data) 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        log_data = request.json 
        if isinstance(log_data, dict): 
            log_data = [log_data] 
        elif not isinstance(log_data, list): 
            return jsonify({'error': 'Invalid input format'}), 400 
        results = [] 
        for log_entry in log_data: 
            score = 0.0 
            is_anomaly = False 
            results.append({ 
                'log_id': log_entry.get('id', 'unknown'), 
                'score': score, 
                'is_anomaly': is_anomaly, 
                'severity': 'normal' 
            }) 
        return jsonify({ 
            'results': results, 
            'total_processed': len(results), 
            'anomalies_detected': sum(1 for r in results if r['is_anomaly']) 
        }) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
 
# Initialize model 
model = IsolationForest(contamination=0.1, random_state=42) 
scaler = StandardScaler() 
 
sample_data = np.array([[8, 1, 1, 1, 443, 1024, 1]]) 
scaler.fit(sample_data) 
scaled_data = scaler.transform(sample_data) 
model.fit(scaled_data) 
 
@app.route('/health', methods=['GET']) 
def health_check(): 
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}) 
 
@app.route('/detect', methods=['POST']) 
def detect_anomaly(): 
    try: 
        log_data = request.json 
        if isinstance(log_data, dict): 
            log_data = [log_data] 
        elif not isinstance(log_data, list): 
            return jsonify({'error': 'Invalid input format'}), 400 
        results = [] 
        for log_entry in log_data: 
            score = 0.0 
            is_anomaly = False 
            results.append({ 
                'log_id': log_entry.get('id', 'unknown'), 
                'score': score, 
                'is_anomaly': is_anomaly, 
                'severity': 'normal' 
            }) 
        return jsonify({ 
            'results': results, 
            'total_processed': len(results), 
            'anomalies_detected': sum(1 for r in results if r['is_anomaly']) 
        }) 
    except Exception as e: 
        return jsonify({'error': str(e)}), 500 
 
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=8080, debug=False) 
