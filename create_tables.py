#!/usr/bin/env python3
"""
Script to create tables in Supabase for the Ubik Whisper API
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ubik-whisper-api")

# Load environment variables
load_dotenv(override=True)

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    sys.exit(1)

def create_tables():
    """
    Create tables in Supabase using the REST API
    """
    logger.info("Creating tables in Supabase...")
    
    try:
        # Initialize Supabase client
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Connected to Supabase successfully!")
        
        # Create transcriptions table
        logger.info("Creating transcriptions table...")
        
        # Use the REST API to create the table
        # Note: This is a workaround since the Python client doesn't support direct SQL execution
        try:
            # First check if the table exists by trying to select from it
            client.table("transcriptions").select("id").limit(1).execute()
            logger.info("Transcriptions table already exists!")
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                # Create the table using the REST API
                # We'll use the RPC function to execute SQL
                result = client.rpc(
                    "execute_sql", 
                    {
                        "query": """
                        CREATE TABLE IF NOT EXISTS public.transcriptions (
                            id UUID PRIMARY KEY,
                            status TEXT NOT NULL,
                            progress FLOAT NOT NULL,
                            chunks JSONB,
                            full_transcription TEXT,
                            error TEXT,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                        """
                    }
                ).execute()
                logger.info("Transcriptions table created successfully!")
            else:
                raise e
        
        # Create summaries table
        logger.info("Creating summaries table...")
        try:
            # First check if the table exists by trying to select from it
            client.table("summaries").select("id").limit(1).execute()
            logger.info("Summaries table already exists!")
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                # Create the table using the REST API
                result = client.rpc(
                    "execute_sql", 
                    {
                        "query": """
                        CREATE TABLE IF NOT EXISTS public.summaries (
                            id UUID PRIMARY KEY,
                            transcribe_id UUID NOT NULL,
                            status TEXT NOT NULL,
                            progress FLOAT NOT NULL,
                            summary TEXT,
                            error TEXT,
                            metadata JSONB,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                        """
                    }
                ).execute()
                logger.info("Summaries table created successfully!")
            else:
                raise e
        
        # Create function for updating timestamps
        logger.info("Creating updated_at function...")
        result = client.rpc(
            "execute_sql", 
            {
                "query": """
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                """
            }
        ).execute()
        logger.info("Updated_at function created successfully!")
        
        # Create triggers
        logger.info("Creating triggers...")
        
        # Transcriptions trigger
        result = client.rpc(
            "execute_sql", 
            {
                "query": """
                DROP TRIGGER IF EXISTS update_transcriptions_updated_at ON public.transcriptions;
                CREATE TRIGGER update_transcriptions_updated_at
                BEFORE UPDATE ON public.transcriptions
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
                """
            }
        ).execute()
        logger.info("Transcriptions trigger created successfully!")
        
        # Summaries trigger
        result = client.rpc(
            "execute_sql", 
            {
                "query": """
                DROP TRIGGER IF EXISTS update_summaries_updated_at ON public.summaries;
                CREATE TRIGGER update_summaries_updated_at
                BEFORE UPDATE ON public.summaries
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
                """
            }
        ).execute()
        logger.info("Summaries trigger created successfully!")
        
        # Create storage bucket
        logger.info("Creating storage bucket for audio files...")
        try:
            buckets = client.storage.list_buckets()
            
            if not any(bucket.name == "audio_files" for bucket in buckets):
                client.storage.create_bucket("audio_files", {"public": False})
                logger.info("Storage bucket 'audio_files' created successfully!")
            else:
                logger.info("Storage bucket 'audio_files' already exists!")
        except Exception as e:
            logger.error(f"Error creating storage bucket: {e}")
        
        logger.info("Database setup completed successfully!")
        
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_tables()
