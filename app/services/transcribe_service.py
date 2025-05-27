import os
import tempfile
import uuid
import asyncio
import logging
from typing import List, Dict, Any, Optional
import aiofiles
from pydub import AudioSegment
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

from app.models.models import StatusEnum, TranscriptionData, ChunkInfo
from app.services.supabase_service import (
    get_supabase_client,
    create_transcription_job,
    update_transcription_job,
    get_transcription_job,
    save_file
)
from app.utils.error_handlers import TranscriptionError, ResourceNotFoundError
from app.utils.audio_utils import load_audio_file, split_audio_file, cleanup_temp_files

# Configure logging
logger = logging.getLogger("ubik-whisper-api")

# Load environment variables
load_dotenv(override=True)

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)
async_client = AsyncOpenAI(api_key=openai_api_key)

# Constants
CHUNK_DURATION_MS = 3 * 60 * 1000  # 3 minutes in milliseconds


async def process_audio_file(file_path: str, transcription_id: str) -> None:
    """
    Process an audio file for transcription
    """
    client = get_supabase_client()
    temp_files = [file_path]  # Track temporary files for cleanup
    
    try:
        logger.info(f"Starting transcription process for job {transcription_id}")
        
        # Update job status to processing
        transcription_data = TranscriptionData(
            id=transcription_id,
            status=StatusEnum.PROCESSING,
            progress=0,
            chunks=[]
        )
        await update_transcription_job(client, transcription_data)
        
        # Upload file to Supabase storage
        # Use the original file extension or default to .m4a
        file_ext = os.path.splitext(file_path)[1] or ".m4a"
        file_name = f"{transcription_id}{file_ext}"
        logger.info(f"Uploading file to Supabase storage: {file_name}")
        file_url = await save_file(client, file_path, file_name)
        
        # Load audio file
        logger.info(f"Loading audio file: {file_path}")
        try:
            audio = load_audio_file(file_path)
        except Exception as e:
            logger.error(f"Error loading audio file: {e}")
            raise TranscriptionError(f"Failed to load audio file: {str(e)}")
        
        # Split audio into chunks
        logger.info(f"Splitting audio into chunks (duration: {CHUNK_DURATION_MS/1000/60} minutes)")
        chunks = split_audio_file(audio, CHUNK_DURATION_MS)
        total_chunks = len(chunks)
        logger.info(f"Audio split into {total_chunks} chunks")
        
        # Add chunk files to temp_files list for cleanup
        for _, _, chunk_path in chunks:
            temp_files.append(chunk_path)
        
        # Process each chunk
        transcription_chunks = []
        for i, (start_time, end_time, chunk_path) in enumerate(chunks):
            logger.info(f"Transcribing chunk {i+1}/{total_chunks} ({start_time/1000}s to {end_time/1000}s)")
            
            # Transcribe chunk
            try:
                text = await transcribe_chunk(chunk_path)
            except Exception as e:
                logger.error(f"Error transcribing chunk {i+1}: {e}")
                raise TranscriptionError(f"Failed to transcribe chunk {i+1}: {str(e)}")
            
            # Create chunk info
            chunk_info = ChunkInfo(
                start_time=start_time / 1000,  # Convert to seconds
                end_time=end_time / 1000,      # Convert to seconds
                text=text
            )
            transcription_chunks.append(chunk_info)
            
            # Update progress
            progress = (i + 1) / total_chunks
            transcription_data.progress = progress
            transcription_data.chunks = transcription_chunks
            await update_transcription_job(client, transcription_data)
            
            # Clean up temporary chunk file
            try:
                os.remove(chunk_path)
                temp_files.remove(chunk_path)  # Remove from cleanup list
            except Exception as e:
                logger.warning(f"Failed to remove temporary chunk file: {e}")
        
        # Combine all transcriptions
        logger.info(f"Combining {len(transcription_chunks)} chunk transcriptions")
        full_transcription = "\n\n".join([chunk.text for chunk in transcription_chunks])
        
        # Update job as completed
        logger.info(f"Transcription completed for job {transcription_id}")
        transcription_data.status = StatusEnum.COMPLETED
        transcription_data.progress = 1.0
        transcription_data.full_transcription = full_transcription
        await update_transcription_job(client, transcription_data)
        
    except Exception as e:
        logger.error(f"Transcription failed for job {transcription_id}: {e}")
        
        # Update job as failed
        transcription_data = TranscriptionData(
            id=transcription_id,
            status=StatusEnum.FAILED,
            progress=0,
            error=str(e)
        )
        await update_transcription_job(client, transcription_data)
        
        # Re-raise as TranscriptionError if it's not already
        if not isinstance(e, TranscriptionError):
            raise TranscriptionError(str(e))
        raise
        
    finally:
        # Clean up all temporary files
        cleanup_temp_files(temp_files)





async def transcribe_chunk(chunk_path: str) -> str:
    """
    Transcribe an audio chunk using OpenAI's Whisper model
    """
    try:
        with open(chunk_path, "rb") as audio_file:
            # Using the new client-based API for audio transcription
            response = await async_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        if not response or not hasattr(response, 'text'):
            raise TranscriptionError("Received invalid response from OpenAI Whisper API")
        
        return response.text
    except Exception as e:
        logger.error(f"Error in transcribe_chunk: {e}")
        raise TranscriptionError(f"Failed to transcribe audio chunk: {str(e)}")


async def get_transcription_status(transcription_id: str) -> TranscriptionData:
    """
    Get the status of a transcription job
    
    Args:
        transcription_id: The ID of the transcription job
        
    Returns:
        TranscriptionData object
        
    Raises:
        ResourceNotFoundError: If the transcription job is not found
    """
    client = get_supabase_client()
    transcription_data = await get_transcription_job(client, transcription_id)
    
    if not transcription_data:
        logger.error(f"Transcription job not found: {transcription_id}")
        raise ResourceNotFoundError(f"Transcription job with ID {transcription_id} not found")
    
    return transcription_data
