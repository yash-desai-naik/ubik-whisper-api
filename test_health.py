#!/usr/bin/env python3
"""
Simple test script to check if the API is running correctly
"""
import requests

def test_health():
    """Test the health endpoint"""
    print("Testing health endpoint...")
    response = requests.get("http://127.0.0.1:8000/health")
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

if __name__ == "__main__":
    if test_health():
        print("\n✅ API is running correctly!")
    else:
        print("\n❌ API health check failed!")
