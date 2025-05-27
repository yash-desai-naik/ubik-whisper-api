import os
import re
import asyncio
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

from app.models.models import StatusEnum, SummaryData, TranscriptionData
from app.services.supabase_service import (
    get_supabase_client,
    create_summary_job,
    update_summary_job,
    get_summary_job,
    get_transcription_job,
)
from app.utils.error_handlers import SummarizationError, ResourceNotFoundError, InvalidRequestError
from app.utils.text_utils import split_text_into_chunks, extract_metadata_from_text, format_summary

# Configure logging
logger = logging.getLogger("ubik-whisper-api")

# Load environment variables
load_dotenv(override=True)

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)
async_client = AsyncOpenAI(api_key=openai_api_key)

# Constants
MAX_TOKENS_PER_CHUNK = 4000  # Maximum tokens per chunk for GPT processing
MODEL_NAME = "gpt-4.1-mini"  # OpenAI model to use for summarization


async def process_transcription(transcription_id: str, summary_id: str) -> None:
    """
    Process a transcription for summarization
    """
    client = get_supabase_client()
    
    try:
        logger.info(f"Starting summarization process for job {summary_id} (transcription: {transcription_id})")
        
        # Get transcription data
        try:
            transcription_data = await get_transcription_job(client, transcription_id)
            
            if not transcription_data:
                raise ResourceNotFoundError(f"Transcription with ID {transcription_id} not found")
            
            if transcription_data.status != StatusEnum.COMPLETED:
                raise InvalidRequestError(f"Transcription with ID {transcription_id} is not completed (status: {transcription_data.status})")
            
            if not transcription_data.full_transcription:
                raise InvalidRequestError(f"Transcription with ID {transcription_id} has no content")
                
        except Exception as e:
            logger.error(f"Error retrieving transcription data: {e}")
            if isinstance(e, (ResourceNotFoundError, InvalidRequestError)):
                raise
            raise SummarizationError(f"Failed to retrieve transcription data: {str(e)}")
        
        # Update summary job status to processing
        summary_data = SummaryData(
            id=summary_id,
            transcribe_id=transcription_id,
            status=StatusEnum.PROCESSING,
            progress=0
        )
        await update_summary_job(client, summary_data)
        
        # Split transcription into chunks
        logger.info(f"Splitting transcription into chunks (max tokens per chunk: {MAX_TOKENS_PER_CHUNK})")
        transcription_chunks = split_text_into_chunks(transcription_data.full_transcription, MAX_TOKENS_PER_CHUNK)
        total_chunks = len(transcription_chunks)
        logger.info(f"Transcription split into {total_chunks} chunks")
        
        # Process each chunk for initial summaries
        chunk_summaries = []
        for i, chunk in enumerate(transcription_chunks):
            logger.info(f"Summarizing chunk {i+1}/{total_chunks} (length: {len(chunk)} chars)")
            
            # Summarize chunk
            try:
                chunk_summary = await summarize_chunk(chunk)
                chunk_summaries.append(chunk_summary)
            except Exception as e:
                logger.error(f"Error summarizing chunk {i+1}: {e}")
                raise SummarizationError(f"Failed to summarize chunk {i+1}: {str(e)}")
            
            # Update progress (50% of the process is chunk summarization)
            progress = (i + 1) / total_chunks * 0.5
            summary_data.progress = progress
            await update_summary_job(client, summary_data)
        
        # Combine chunk summaries and create final summary
        logger.info(f"Combining {len(chunk_summaries)} chunk summaries")
        combined_summary = "\n\n".join(chunk_summaries)
        
        # Update progress (75% complete after combining summaries)
        summary_data.progress = 0.75
        await update_summary_job(client, summary_data)
        
        # Create final comprehensive summary with metadata extraction
        logger.info("Creating final comprehensive summary with metadata extraction")
        try:
            final_summary, metadata = await create_final_summary(combined_summary)
        except Exception as e:
            logger.error(f"Error creating final summary: {e}")
            raise SummarizationError(f"Failed to create final summary: {str(e)}")
        
        # Update job as completed
        logger.info(f"Summarization completed for job {summary_id}")
        summary_data.status = StatusEnum.COMPLETED
        summary_data.progress = 1.0
        summary_data.summary = final_summary
        summary_data.metadata = metadata
        await update_summary_job(client, summary_data)
        
    except Exception as e:
        logger.error(f"Summarization failed for job {summary_id}: {e}")
        
        # Update job as failed
        summary_data = SummaryData(
            id=summary_id,
            transcribe_id=transcription_id,
            status=StatusEnum.FAILED,
            progress=0,
            error=str(e)
        )
        await update_summary_job(client, summary_data)
        
        # Re-raise as SummarizationError if it's not already
        if not isinstance(e, (SummarizationError, ResourceNotFoundError, InvalidRequestError)):
            raise SummarizationError(str(e))
        raise





async def summarize_chunk(chunk: str) -> str:
    """
    Summarize a chunk of text using OpenAI's GPT model
    """
    try:
        response = await async_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes text accurately and concisely."},
                {"role": "user", "content": f"Please summarize the following text, preserving key information, quotes, and details:\n\n{chunk}"}
            ],
            max_tokens=1500,
            temperature=0.3
        )
        
        if not response or not hasattr(response, 'choices') or not response.choices:
            raise SummarizationError("Received invalid response from OpenAI API")
            
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error in summarize_chunk: {e}")
        raise SummarizationError(f"Failed to summarize text chunk: {str(e)}")


async def create_final_summary(combined_summaries: str) -> tuple:
    """
    Create a final comprehensive summary with metadata extraction
    Returns a tuple of (final_summary, metadata)
    """
    try:
        response = await async_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": """You are a helpful assistant that creates well-structured, comprehensive summaries.
                Your task is to create a final summary from the provided text, which consists of summaries of different parts of a transcription.
                IMPORTANT: Auto-correct any misspelled words and names. and mention e.g. "John (Auto-corrected)", "New York (Auto-corrected)" etc. use your intelligence to correct any misspelled words and names, locations..eg. "Bodidhara, Gujarat" would be "Vadodara, Gujarat" etc.
                Format (markdown) the summary according to the topic and discussion. Make it well-structured with clear sections.
                At the end, extract and list the following metadata only if available:
                1. Dates mentioned
                2. Links/URLs mentioned
                3. References to documents, books, papers, locations, etc.
                4. People mentioned
                5. Organizations mentioned
                6. Key topics discussed
                7. Any other relevant information"""},
                {"role": "user", "content": f"Here are the summaries to combine into a final comprehensive summary:\n\n{combined_summaries}"}
            ],
            max_tokens=2000,
            temperature=0.3
        )
        
        if not response or not hasattr(response, 'choices') or not response.choices:
            raise SummarizationError("Received invalid response from OpenAI API")
        
        summary_text = response.choices[0].message.content
        
        # Extract metadata from the summary
        metadata = extract_metadata_from_text(summary_text)
        
        # Format the summary with the extracted metadata
        formatted_summary = format_summary(summary_text, metadata)
        
        return formatted_summary, metadata
    except Exception as e:
        logger.error(f"Error in create_final_summary: {e}")
        raise SummarizationError(f"Failed to create final summary: {str(e)}")





async def get_summary_status(summary_id: str) -> SummaryData:
    """
    Get the status of a summary job
    
    Args:
        summary_id: The ID of the summary job
        
    Returns:
        SummaryData object
        
    Raises:
        ResourceNotFoundError: If the summary job is not found
    """
    client = get_supabase_client()
    summary_data = await get_summary_job(client, summary_id)
    
    if not summary_data:
        logger.error(f"Summary job not found: {summary_id}")
        raise ResourceNotFoundError(f"Summary job with ID {summary_id} not found")
    
    return summary_data
