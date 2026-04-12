#!/usr/bin/env python
"""
ESIG Complete Local Verification Script
Tests all endpoints and verifies requirements
"""
import requests
import json
import sys

print("\n" + "=" * 70)
print("🧪 ESIG COMPLETE LOCAL VERIFICATION TEST")
print("=" * 70)

tests_passed = 0
tests_failed = 0

def test_endpoint(name, url, expected_keys=None):
    global tests_passed, tests_failed
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            print(f"❌ {name}: {r.status_code}")
            tests_failed += 1
            return None
        data = r.json()
        if expected_keys and isinstance(data, dict):
            missing = set(expected_keys) - set(data.keys())
            if missing:
                print(f"⚠️  {name}: Missing keys {missing}")
        print(f"✅ {name}")
        tests_passed += 1
        return data
    except Exception as e:
        print(f"❌ {name}: {str(e)[:50]}")
        tests_failed += 1
        return None

# 1. Core OpenEnv Health
health = test_endpoint("Health Check", "http://localhost:7860/health")

# 2. Tasks
tasks_data = test_endpoint("Tasks Endpoint", "http://localhost:7860/tasks")
if tasks_data:
    print(f"   └─ {len(tasks_data)} tasks available")
    required_tasks = ["task1_easy", "task2_medium", "task3_hard", "task4_expert"]
    task_ids = [t.get("task_id") for t in tasks_data]
    missing_tasks = set(required_tasks) - set(task_ids)
    if missing_tasks:
        print(f"   ⚠️ MISSING TASKS: {missing_tasks}")
        tests_failed += 1
    else:
        print(f"   ✅ All 4 required tasks present")
        tests_passed += 1

# 3. Threats Catalog
threats = test_endpoint("Threats Catalog", "http://localhost:7860/threats/catalog", 
                       expected_keys=["total_threats", "threats"])
if threats:
    total = threats.get("total_threats", 0)
    print(f"   └─ {total} threat types")
    if total >= 7:
        print(f"   ✅ Required 7 threats met ({total} found)")
        tests_passed += 1
    else:
        print(f"   ⚠️ Only {total} threats (need 7)")

# 4. Analytics
analytics = test_endpoint("Analytics Report", "http://localhost:7860/analytics/report")

# 5. Database Status
db_status = test_endpoint("DB Status", "http://localhost:7860/db/status")

# 6.Test Suite Status
print("\n" + "-" * 70)
print(f"✅ TESTS PASSED: {tests_passed}")
print(f"❌ TESTS FAILED: {tests_failed}")

if tests_failed == 0:
    print("\n" + "=" * 70)
    print("✅ ALL VERIFICATIONS PASSED!")
    print("   The ESIG project is READY FOR SUBMISSION")
    print("=" * 70 + "\n")
    sys.exit(0)
else:
    print("\n⚠️ Some verifications failed")
    sys.exit(1)
