from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any
import os
import uuid
import tempfile
import logging
import aiofiles
from supabase import Client

from app.models.models import TranscribeResponse, TranscribeStatusResponse
from app.services.supabase_service import get_supabase_client, create_transcription_job
from app.services.transcribe_service import process_audio_file, get_transcription_status
from app.utils.error_handlers import TranscriptionError, ResourceNotFoundError, InvalidRequestError

# Configure logging
logger = logging.getLogger("ubik-whisper-api")

router = APIRouter(tags=["Transcribe"])

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    client: Client = Depends(get_supabase_client)
):
    """
    Submit an audio file for transcription
    """
    temp_file_path = None
    
    try:
        # Check if file is an audio file with supported format
        supported_formats = [".m4a", ".mp3", ".wav", ".mp4", ".mpeg", ".mpga", ".m4a", ".webm"]
        file_ext = os.path.splitext(file.filename.lower())[1]
        
        if not file_ext or file_ext not in supported_formats:
            logger.warning(f"Unsupported file format: {file.filename}")
            raise InvalidRequestError(f"Unsupported file format: {file_ext}. Supported formats are: {', '.join(supported_formats)}")
        
        # Check if file is empty
        if not file.file:
            logger.warning("Empty file uploaded")
            raise InvalidRequestError("Empty file uploaded")
        
        # Generate a unique ID for the transcription job
        transcription_id = str(uuid.uuid4())
        logger.info(f"Creating new transcription job: {transcription_id}")
        
        # Save the uploaded file to a temporary location
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".m4a")
        temp_file_path = temp_file.name
        temp_file.close()
        
        logger.info(f"Saving uploaded file to temporary location: {temp_file_path}")
        async with aiofiles.open(temp_file_path, "wb") as f:
            content = await file.read()
            if not content:
                raise InvalidRequestError("File content is empty")
            await f.write(content)
        
        # Create transcription job in the database
        logger.info(f"Creating transcription job in database: {transcription_id}")
        await create_transcription_job(client, transcription_id)
        
        # Process the audio file in the background
        logger.info(f"Starting background transcription process: {transcription_id}")
        background_tasks.add_task(process_audio_file, temp_file_path, transcription_id)
        
        return TranscribeResponse(
            id=transcription_id,
            status="pending",
            progress=0
        )
        
    except Exception as e:
        # Clean up temporary file if it exists
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temporary file: {cleanup_error}")
        
        # Log the error
        logger.error(f"Error in transcribe_audio: {e}")
        
        # Handle specific errors
        if isinstance(e, InvalidRequestError):
            raise HTTPException(status_code=400, detail=str(e))
        elif isinstance(e, TranscriptionError):
            raise HTTPException(status_code=500, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/transcribe/status/{transcription_id}", response_model=TranscribeStatusResponse)
async def get_transcription_job_status(transcription_id: str):
    """
    Get the status of a transcription job
    """
    try:
        logger.info(f"Getting status for transcription job: {transcription_id}")
        
        # Get transcription job status
        transcription_data = await get_transcription_status(transcription_id)
        
        logger.info(f"Transcription job status: {transcription_data.status}, progress: {transcription_data.progress}")
        
        return TranscribeStatusResponse(
            id=transcription_data.id,
            status=transcription_data.status,
            progress=transcription_data.progress,
            transcription=transcription_data.full_transcription,
            error=transcription_data.error
        )
        
    except ResourceNotFoundError as e:
        logger.warning(f"Transcription job not found: {transcription_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting transcription job status: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
