#!/usr/bin/env python3
"""
Test script for the Background Remover API
"""

import requests
import json
import sys
import os

def test_api(base_url="http://localhost:5000"):
    """Test all API endpoints"""
    
    print(f"Testing Background Remover API at {base_url}")
    print("=" * 50)
    
    # Test 1: API Info
    print("1. Testing API info endpoint...")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Version: {data['version']}")
            print(f"✅ Max file size: {data['max_file_size_mb']}MB")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Health check
    print("\n2. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data['status']}")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Models endpoint
    print("\n3. Testing models endpoint...")
    try:
        response = requests.get(f"{base_url}/models")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Available models: {len(data['models'])}")
            print(f"✅ Default model: {data['default']}")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Background removal (if test image exists)
    test_image_path = "test_image.png"
    if os.path.exists(test_image_path):
        print("\n4. Testing background removal...")
        try:
            with open(test_image_path, 'rb') as f:
                files = {'image': f}
                data = {'return_base64': 'true', 'model': 'u2net', 'format': 'png'}
                response = requests.post(f"{base_url}/remove-background", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✅ Background removal successful")
                    print(f"✅ Model used: {result.get('model_used')}")
                    print(f"✅ Original size: {result.get('original_size')}")
                    print(f"✅ Output format: {result.get('format')}")
                else:
                    print(f"❌ API returned error: {result}")
            else:
                print(f"❌ Failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"❌ Error: {error_data}")
                except:
                    print(f"❌ Response: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print(f"\n4. Skipping background removal test (no {test_image_path} found)")
    
    print("\n" + "=" * 50)
    print("API testing completed!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:5000"
    
    test_api(base_url)