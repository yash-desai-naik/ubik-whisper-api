from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any
import uuid
import logging
from supabase import Client

from app.models.models import SummarizeRequest, SummarizeResponse, SummarizeStatusResponse
from app.services.supabase_service import get_supabase_client, create_summary_job
from app.services.summarize_service import process_transcription, get_summary_status
from app.services.transcribe_service import get_transcription_status
from app.utils.error_handlers import SummarizationError, ResourceNotFoundError, InvalidRequestError

# Configure logging
logger = logging.getLogger("ubik-whisper-api")

router = APIRouter(tags=["Summarize"])

@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_transcription(
    request: SummarizeRequest,
    background_tasks: BackgroundTasks,
    client: Client = Depends(get_supabase_client)
):
    """
    Submit a transcription for summarization
    """
    try:
        logger.info(f"Received summarization request for transcription: {request.transcribe_id}")
        
        # Validate request
        if not request.transcribe_id:
            logger.warning("Empty transcribe_id in summarization request")
            raise InvalidRequestError("transcribe_id is required")
        
        # Check if transcription exists and is completed
        try:
            logger.info(f"Checking transcription status: {request.transcribe_id}")
            transcription_data = await get_transcription_status(request.transcribe_id)
            
            # Status check is now handled in get_transcription_status with proper error handling
            if transcription_data.status.value != "completed":
                logger.warning(f"Transcription not completed: {request.transcribe_id} (status: {transcription_data.status.value})")
                raise InvalidRequestError(
                    f"Transcription with ID {request.transcribe_id} is not completed (status: {transcription_data.status.value})"
                )
                
            if not transcription_data.full_transcription:
                logger.warning(f"Transcription has no content: {request.transcribe_id}")
                raise InvalidRequestError(f"Transcription with ID {request.transcribe_id} has no content")
                
        except ResourceNotFoundError as e:
            logger.warning(f"Transcription not found: {request.transcribe_id}")
            raise HTTPException(status_code=404, detail=str(e))
        except InvalidRequestError as e:
            logger.warning(f"Invalid request: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        
        # Generate a unique ID for the summary job
        summary_id = str(uuid.uuid4())
        logger.info(f"Creating new summary job: {summary_id}")
        
        # Create summary job in the database
        logger.info(f"Creating summary job in database: {summary_id}")
        await create_summary_job(client, summary_id, request.transcribe_id)
        
        # Process the transcription in the background
        logger.info(f"Starting background summarization process: {summary_id}")
        background_tasks.add_task(process_transcription, request.transcribe_id, summary_id)
        
        return SummarizeResponse(
            id=summary_id,
            status="pending",
            progress=0
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        logger.error(f"Error in summarize_transcription: {e}")
        
        # Handle specific errors
        if isinstance(e, InvalidRequestError):
            raise HTTPException(status_code=400, detail=str(e))
        elif isinstance(e, SummarizationError):
            raise HTTPException(status_code=500, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/summarize/status/{summary_id}", response_model=SummarizeStatusResponse)
async def get_summary_job_status(summary_id: str):
    """
    Get the status of a summary job
    """
    try:
        logger.info(f"Getting status for summary job: {summary_id}")
        
        # Get summary job status
        summary_data = await get_summary_status(summary_id)
        
        logger.info(f"Summary job status: {summary_data.status}, progress: {summary_data.progress}")
        
        return SummarizeStatusResponse(
            id=summary_data.id,
            status=summary_data.status,
            progress=summary_data.progress,
            summary=summary_data.summary,
            error=summary_data.error
        )
        
    except ResourceNotFoundError as e:
        logger.warning(f"Summary job not found: {summary_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting summary job status: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
