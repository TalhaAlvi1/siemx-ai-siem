#!/usr/bin/env python3
"""SIEMX Kibana Launcher - Python script to manage Kibana"""

import os, sys, time, subprocess, requests, webbrowser

print("="*80)
print("🚀 SIEMX KIBANA MANAGER")
print("="*80)

# Check if ELK stack installed
elk_dir = "elk-stack"
if not os.path.exists(elk_dir):
   print("\n❌ ELK Stack not installed!")
   print("\n💡 To install:")
   print("   1. Install Java 17+ first")
   print("  2. Run: .\\INSTALL_ELK_STACK.bat")
   print("   3. Then run this script again")
    sys.exit(0)

# Menu
while True:
   print("\n" + "="*80)
   print("MENU:")
   print("1. Check Status")
   print("2. Start Elasticsearch")
   print("3. Start Kibana")
   print("4. Start All Services")
   print("5. Open Browser to Kibana")
   print("6. Console Dashboard Preview")
   print("7. Exit")
   print("="*80)
    
    choice = input("\nEnter choice (1-7): ").strip()
    
   if choice == '1':
        # Check Elasticsearch
        try:
            r = requests.get('http://localhost:9200/_cluster/health', timeout=5)
           if r.status_code == 200:
               print(f"\n✅ Elasticsearch: RUNNING ({r.json().get('status')})")
            else:
               print("\n⚠️  Elasticsearch: Issues")
       except:
           print("\n❌ Elasticsearch: OFFLINE")
        
        # Check Kibana
        try:
           r = requests.get('http://localhost:5601/api/status', timeout=5)
           if r.status_code == 200:
               print("✅ Kibana: RUNNING")
            else:
               print("⚠️  Kibana: Issues")
       except:
           print("❌ Kibana: OFFLINE")
    
    elif choice == '2':
       print("\n🚀 Starting Elasticsearch...")
        es_path = os.path.join(elk_dir, 'elasticsearch-8.12.0', 'bin', 'elasticsearch.bat')
       if os.path.exists(es_path):
            subprocess.Popen(['cmd', '/K', f'cd /d "{os.path.dirname(es_path)}" && elasticsearch.bat'], 
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
           print("⏳ Wait 30 seconds for initialization...")
           time.sleep(30)
           print("✅ Elasticsearch starting!")
        else:
           print("❌ Elasticsearch not found. Run INSTALL_ELK_STACK.bat first.")
    
    elif choice == '3':
       print("\n🚀 Starting Kibana...")
        kb_path = os.path.join(elk_dir, 'kibana-8.12.0', 'bin', 'kibana.bat')
       if os.path.exists(kb_path):
            subprocess.Popen(['cmd', '/K', f'cd /d "{os.path.dirname(kb_path)}" && kibana.bat'],
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
           print("⏳ Wait 60 seconds for initialization...")
           time.sleep(60)
           print("✅ Kibana starting!")
        else:
           print("❌ Kibana not found. Run INSTALL_ELK_STACK.bat first.")
    
    elif choice == '4':
       print("\n🚀 Starting All Services...")
        # Start ES
        es_path = os.path.join(elk_dir, 'elasticsearch-8.12.0', 'bin', 'elasticsearch.bat')
       if os.path.exists(es_path):
            subprocess.Popen(['cmd', '/K', f'cd /d "{os.path.dirname(es_path)}" && elasticsearch.bat'],
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
           print("⏳ Starting Elasticsearch (wait 30s)...")
           time.sleep(30)
        else:
           print("❌ Elasticsearch not found")
        
        # Start Kibana
        kb_path = os.path.join(elk_dir, 'kibana-8.12.0', 'bin', 'kibana.bat')
       if os.path.exists(kb_path):
            subprocess.Popen(['cmd', '/K', f'cd /d "{os.path.dirname(kb_path)}" && kibana.bat'],
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
           print("⏳ Starting Kibana (wait 60s)...")
           time.sleep(60)
           print("✅ All services starting!")
        else:
           print("❌ Kibana not found")
    
    elif choice == '5':
       print("\n🌐 Opening Kibana in browser...")
        webbrowser.open('http://localhost:5601')
       print("✅ Browser opened!")
    
    elif choice == '6':
       print("\n📊 Console Dashboard Preview:")
       print("="*80)
        viz_script = "visualize_siemx.py"
       if os.path.exists(viz_script):
            subprocess.run(['python', viz_script], timeout=30)
        else:
           print("❌ Visualizer not found")
       print("="*80)
    
    elif choice == '7':
       print("\n👋 Goodbye!")
        break
    
    else:
       print("❌ Invalid choice")