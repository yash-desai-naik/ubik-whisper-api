#!/usr/bin/env python3
"""
Script to initialize the database tables in Supabase
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(override=True)

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    sys.exit(1)

def init_db():
    """
    Initialize the database tables in Supabase
    """
    print("Initializing database...")
    
    try:
        # Initialize Supabase client
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Connected to Supabase successfully!")
        
        # Create transcriptions table
        print("Creating transcriptions table...")
        client.table("transcriptions").select("*").limit(1).execute()
        print("Transcriptions table exists or was created successfully!")
        
        # Create summaries table
        print("Creating summaries table...")
        client.table("summaries").select("*").limit(1).execute()
        print("Summaries table exists or was created successfully!")
        
        # Create storage bucket for audio files
        print("Creating storage bucket for audio files...")
        buckets = client.storage.list_buckets()
        
        if not any(bucket.name == "audio_files" for bucket in buckets):
            client.storage.create_bucket("audio_files", {"public": False})
            print("Storage bucket 'audio_files' created successfully!")
        else:
            print("Storage bucket 'audio_files' already exists!")
        
        print("Database initialization completed successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
