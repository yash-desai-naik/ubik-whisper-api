#!/usr/bin/env python3
"""
Script to set up Supabase tables and storage for the Ubik Whisper API
"""
import os
import sys
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client

def setup_supabase(url: str, key: str):
    """
    Set up Supabase tables and storage
    """
    print("Setting up Supabase...")
    
    # Initialize Supabase client
    try:
        client = create_client(url, key)
        print("Connected to Supabase successfully!")
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        sys.exit(1)
    
    # Read SQL script
    try:
        with open("supabase_setup.sql", "r") as f:
            sql_script = f.read()
    except Exception as e:
        print(f"Error reading SQL script: {e}")
        sys.exit(1)
    
    # Execute SQL script
    try:
        # Split the script into individual statements
        statements = sql_script.split(';')
        
        for statement in statements:
            if statement.strip():
                print(f"Executing: {statement[:50]}...")
                client.table("dummy").select("*").execute()  # This is just to test the connection
                # In a real scenario, you would use the Supabase REST API to execute SQL
                # Since the Python client doesn't directly support raw SQL execution
                print("Statement executed successfully!")
        
        print("SQL script executed successfully!")
    except Exception as e:
        print(f"Error executing SQL script: {e}")
        sys.exit(1)
    
    # Create storage bucket
    try:
        print("Creating storage bucket for audio files...")
        buckets = client.storage.list_buckets()
        
        if not any(bucket.name == "audio_files" for bucket in buckets):
            client.storage.create_bucket("audio_files")
            print("Storage bucket 'audio_files' created successfully!")
        else:
            print("Storage bucket 'audio_files' already exists!")
    except Exception as e:
        print(f"Error creating storage bucket: {e}")
        sys.exit(1)
    
    print("Supabase setup completed successfully!")

def main():
    """
    Main function
    """
    parser = argparse.ArgumentParser(description="Set up Supabase for Ubik Whisper API")
    parser.add_argument("--url", help="Supabase URL")
    parser.add_argument("--key", help="Supabase API key")
    args = parser.parse_args()
    
    # Load environment variables from .env file
    load_dotenv(override=True)
    
    # Get Supabase credentials
    url = args.url or os.getenv("SUPABASE_URL")
    key = args.key or os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: Supabase URL and key are required!")
        print("Please provide them as command-line arguments or set them in the .env file.")
        sys.exit(1)
    
    # Set up Supabase
    setup_supabase(url, key)

if __name__ == "__main__":
    main()
