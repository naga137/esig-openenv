#!/usr/bin/env python
import requests
import time

print("\n" + "=" * 70)
print("🧪 ESIG LOCAL TESTING")
print("=" * 70)

time.sleep(2)

# Test health
try:
    r = requests.get('http://localhost:7860/health', timeout=5)
    print(f"\n✅ Health Check: {r.status_code}")
    print(f"   {r.json()}")
except Exception as e:
    print(f"\n❌ Health Check Failed: {e}")
    exit(1)

# Test tasks
try:
    r = requests.get('http://localhost:7860/tasks', timeout=5)
    tasks = r.json()
    print(f"\n✅ Tasks: {len(tasks)} available")
    for task_id in tasks:
        print(f"   - {task_id}")
except Exception as e:
    print(f"\n❌ Tasks Failed: {e}")
    exit(1)

# Test threats
try:
    r = requests.get('http://localhost:7860/threats/catalog', timeout=5)
    threats = r.json()
    print(f"\n✅ Threats: {len(threats)} types")
    threat_ids = list(threats.keys())[:3]
    for tid in threat_ids:
        print(f"   - {tid}")
except Exception as e:
    print(f"\n❌ Threats Failed: {e}")
    exit(1)

# Test analytics
try:
    r = requests.get('http://localhost:7860/analytics/report', timeout=5)
    report = r.json()
    print(f"\n✅ Analytics: Episodes tracked")
except Exception as e:
    print(f"\n⚠️ Analytics (optional): {e}")

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED - API IS WORKING LOCALLY!")
print("=" * 70 + "\n")
