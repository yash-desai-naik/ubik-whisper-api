#!/usr/bin/env python3
"""
Test script for the Ubik Whisper API
"""
import os
import sys
import time
import argparse
import requests
from pprint import pprint

def test_health(base_url):
    """Test the health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{base_url}/health")
    print(f"Status code: {response.status_code}")
    pprint(response.json())
    return response.status_code == 200

def test_transcribe(base_url, file_path):
    """Test the transcribe endpoint"""
    print("\n=== Testing Transcribe Endpoint ===")
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return None
    
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "audio/m4a")}
        response = requests.post(f"{base_url}/transcribe", files=files)
    
    print(f"Status code: {response.status_code}")
    if response.status_code == 200:
        pprint(response.json())
        return response.json().get("id")
    else:
        print(f"Error: {response.text}")
        return None

def test_transcribe_status(base_url, transcription_id, wait_for_completion=False):
    """Test the transcribe status endpoint"""
    print(f"\n=== Testing Transcribe Status Endpoint (ID: {transcription_id}) ===")
    
    max_attempts = 60 if wait_for_completion else 1
    attempt = 0
    completed = False
    
    while attempt < max_attempts and not completed:
        response = requests.get(f"{base_url}/transcribe/status/{transcription_id}")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            pprint(data)
            
            if data.get("status") in ["completed", "failed"]:
                completed = True
            elif wait_for_completion:
                print(f"Progress: {data.get('progress', 0) * 100:.2f}%")
                print("Waiting for transcription to complete...")
                time.sleep(5)
        else:
            print(f"Error: {response.text}")
            break
        
        attempt += 1
    
    return completed

def test_summarize(base_url, transcription_id):
    """Test the summarize endpoint"""
    print(f"\n=== Testing Summarize Endpoint (Transcription ID: {transcription_id}) ===")
    
    data = {"transcribe_id": transcription_id}
    response = requests.post(f"{base_url}/summarize", json=data)
    
    print(f"Status code: {response.status_code}")
    if response.status_code == 200:
        pprint(response.json())
        return response.json().get("id")
    else:
        print(f"Error: {response.text}")
        return None

def test_summarize_status(base_url, summary_id, wait_for_completion=False):
    """Test the summarize status endpoint"""
    print(f"\n=== Testing Summarize Status Endpoint (ID: {summary_id}) ===")
    
    max_attempts = 60 if wait_for_completion else 1
    attempt = 0
    completed = False
    
    while attempt < max_attempts and not completed:
        response = requests.get(f"{base_url}/summarize/status/{summary_id}")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            pprint(data)
            
            if data.get("status") in ["completed", "failed"]:
                completed = True
            elif wait_for_completion:
                print(f"Progress: {data.get('progress', 0) * 100:.2f}%")
                print("Waiting for summarization to complete...")
                time.sleep(5)
        else:
            print(f"Error: {response.text}")
            break
        
        attempt += 1
    
    return completed

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test the Ubik Whisper API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--file", help="Path to M4A file for transcription test")
    parser.add_argument("--transcribe-id", help="Transcription ID for status check or summarization")
    parser.add_argument("--summarize-id", help="Summary ID for status check")
    parser.add_argument("--wait", action="store_true", help="Wait for completion of transcription/summarization")
    args = parser.parse_args()
    
    # Test health endpoint
    if not test_health(args.url):
        print("Health check failed. Make sure the API is running.")
        sys.exit(1)
    
    # Test transcribe endpoint
    if args.file:
        transcription_id = test_transcribe(args.url, args.file)
        if transcription_id:
            test_transcribe_status(args.url, transcription_id, args.wait)
    elif args.transcribe_id:
        test_transcribe_status(args.url, args.transcribe_id, args.wait)
    
    # Test summarize endpoint
    if args.transcribe_id and not args.summarize_id:
        summary_id = test_summarize(args.url, args.transcribe_id)
        if summary_id:
            test_summarize_status(args.url, summary_id, args.wait)
    elif args.summarize_id:
        test_summarize_status(args.url, args.summarize_id, args.wait)

if __name__ == "__main__":
    main()
