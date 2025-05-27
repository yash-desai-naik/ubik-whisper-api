from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any
import uvicorn
import os
import logging
from dotenv import load_dotenv

from app.api.health import router as health_router
from app.api.transcribe import router as transcribe_router
from app.api.summarize import router as summarize_router
from app.services.supabase_service import get_supabase_client
from app.utils.error_handlers import APIError, register_error_handlers
from app.utils.audio_utils import ensure_ffmpeg_installed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ubik-whisper-api")

# Load environment variables
load_dotenv(override=True)

# Check for required environment variables
required_env_vars = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    logger.error("Please set these variables in your .env file or environment")

# Initialize FastAPI app
app = FastAPI(
    title="Ubik Whisper API",
    description="API for transcribing and summarizing M4A audio files using OpenAI's Whisper and GPT-4.1-mini models",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register error handlers
register_error_handlers(app)

# Include routers
app.include_router(health_router)
app.include_router(transcribe_router)
app.include_router(summarize_router)

@app.on_event("startup")
async def startup_event():
    """
    Perform startup checks and initialization
    """
    logger.info("Starting Ubik Whisper API")
    
    # Check if ffmpeg is installed
    try:
        ensure_ffmpeg_installed()
        logger.info("ffmpeg is installed and available")
    except Exception as e:
        logger.error(f"ffmpeg check failed: {e}")
    
    # Check Supabase connection
    try:
        client = get_supabase_client()
        # Simple query to test connection
        # Just test the connection without querying a specific table
        client.auth.get_user()
        logger.info("Supabase connection successful")
    except Exception as e:
        logger.error(f"Supabase connection failed: {e}")
        logger.error("Please check your Supabase credentials and connection")
    
    # Check OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OpenAI API key is not set")
    else:
        logger.info("OpenAI API key is set")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "server_error", "message": "An unexpected error occurred"}}
    )

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
