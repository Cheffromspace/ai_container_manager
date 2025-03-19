#!/usr/bin/env python3
import requests
import json
import sys

def refresh_container_tracking():
    """Call the refresh endpoint to reset container tracking"""
    url = "http://localhost:5000/api/containers/refresh"
    
    try:
        print("Refreshing container tracking...")
        response = requests.get(url)
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Message: {result.get('message')}")
            containers = result.get('containers', [])
            if containers:
                print(f"Tracking {len(containers)} containers:")
                for container in containers:
                    print(f"- {container.get('name')} (ID: {container.get('id')}, Status: {container.get('status')})")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {str(e)}")

if __name__ == "__main__":
    refresh_container_tracking()