#!/usr/bin/env python3
import requests
import json
import sys

def check_api():
    """Check if the API is running and responding"""
    url = "http://localhost:5000/api/containers"
    try:
        print(f"Checking API endpoint: {url}")
        response = requests.get(url)
        print(f"API response status: {response.status_code}")
        
        if response.status_code == 200:
            containers = response.json()
            print(f"API reports {len(containers)} containers")
            for container in containers:
                print(f"  - {container.get('name')} (ID: {container.get('id')}, Status: {container.get('status')})")
        else:
            print(f"API error: {response.text}")
    except Exception as e:
        print(f"Request failed: {str(e)}")

def trigger_refresh():
    """Trigger a refresh of container tracking"""
    url = "http://localhost:5000/api/containers/refresh"
    try:
        print(f"Triggering refresh at: {url}")
        # Try POST method (most likely correct based on API code)
        response = requests.post(url)
        print(f"Refresh response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Refresh message: {result.get('message')}")
            if 'containers' in result:
                containers = result.get('containers')
                print(f"Now tracking {len(containers)} containers:")
                for container in containers:
                    print(f"  - {container.get('name')} (ID: {container.get('id')}, Status: {container.get('status')}")
                    
            if 'lost_tracking' in result and result['lost_tracking']:
                lost = result.get('lost_tracking')
                print(f"Lost tracking of {len(lost)} containers:")
                for container in lost:
                    print(f"  - {container.get('name')} (ID: {container.get('id')}, Status: {container.get('status')}")
        else:
            print(f"Refresh error: {response.text}")
    except Exception as e:
        print(f"Refresh failed: {str(e)}")

if __name__ == "__main__":
    print("Step 1: Checking if API is responding and what containers it knows about")
    check_api()
    
    print("\nStep 2: Triggering a refresh of container tracking")
    trigger_refresh()
    
    print("\nStep 3: Checking API again after refresh")
    check_api()