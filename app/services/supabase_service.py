import os
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List
import json
from app.models.models import StatusEnum, TranscriptionData, SummaryData

# Load environment variables
load_dotenv(override=True)

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase_client() -> Client:
    """
    Get Supabase client instance
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and KEY must be set in .env file")
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

async def save_file(client: Client, file_path: str, file_name: str) -> str:
    """
    Upload a file to Supabase storage
    """
    bucket_name = "audio_files"
    
    # Check if bucket exists, if not create it
    buckets = client.storage.list_buckets()
    if not any(bucket.name == bucket_name for bucket in buckets):
        client.storage.create_bucket(bucket_name)
    
    # Upload file
    with open(file_path, "rb") as f:
        file_data = f.read()
    
    response = client.storage.from_(bucket_name).upload(file_name, file_data)
    
    # Get public URL
    file_url = client.storage.from_(bucket_name).get_public_url(file_name)
    
    return file_url

async def create_transcription_job(client: Client, transcription_id: str) -> None:
    """
    Create a new transcription job in the database
    """
    data = {
        "id": transcription_id,
        "status": StatusEnum.PENDING.value,
        "progress": 0,
        "chunks": [],
        "full_transcription": None,
        "error": None
    }
    
    client.table("transcriptions").insert(data).execute()

async def update_transcription_job(client: Client, transcription_data: TranscriptionData) -> None:
    """
    Update an existing transcription job in the database
    """
    data = {
        "status": transcription_data.status.value,
        "progress": transcription_data.progress,
        "chunks": json.dumps([chunk.dict() for chunk in transcription_data.chunks]) if transcription_data.chunks else [],
        "full_transcription": transcription_data.full_transcription,
        "error": transcription_data.error
    }
    
    client.table("transcriptions").update(data).eq("id", transcription_data.id).execute()

async def get_transcription_job(client: Client, transcription_id: str) -> Optional[TranscriptionData]:
    """
    Get a transcription job from the database
    """
    response = client.table("transcriptions").select("*").eq("id", transcription_id).execute()
    
    if not response.data:
        return None
    
    job_data = response.data[0]
    chunks = json.loads(job_data["chunks"]) if job_data["chunks"] and isinstance(job_data["chunks"], str) else []
    
    return TranscriptionData(
        id=job_data["id"],
        status=StatusEnum(job_data["status"]),
        progress=job_data["progress"],
        chunks=chunks,
        full_transcription=job_data["full_transcription"],
        error=job_data["error"]
    )

async def create_summary_job(client: Client, summary_id: str, transcribe_id: str) -> None:
    """
    Create a new summary job in the database
    """
    data = {
        "id": summary_id,
        "transcribe_id": transcribe_id,
        "status": StatusEnum.PENDING.value,
        "progress": 0,
        "summary": None,
        "error": None,
        "metadata": None
    }
    
    client.table("summaries").insert(data).execute()

async def update_summary_job(client: Client, summary_data: SummaryData) -> None:
    """
    Update an existing summary job in the database
    """
    data = {
        "status": summary_data.status.value,
        "progress": summary_data.progress,
        "summary": summary_data.summary,
        "error": summary_data.error,
        "metadata": json.dumps(summary_data.metadata) if summary_data.metadata else None
    }
    
    client.table("summaries").update(data).eq("id", summary_data.id).execute()

async def get_summary_job(client: Client, summary_id: str) -> Optional[SummaryData]:
    """
    Get a summary job from the database
    """
    response = client.table("summaries").select("*").eq("id", summary_id).execute()
    
    if not response.data:
        return None
    
    job_data = response.data[0]
    metadata = json.loads(job_data["metadata"]) if job_data["metadata"] and isinstance(job_data["metadata"], str) else None
    
    return SummaryData(
        id=job_data["id"],
        transcribe_id=job_data["transcribe_id"],
        status=StatusEnum(job_data["status"]),
        progress=job_data["progress"],
        summary=job_data["summary"],
        error=job_data["error"],
        metadata=metadata
    )
