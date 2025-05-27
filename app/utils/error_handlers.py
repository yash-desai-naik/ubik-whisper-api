from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional


class APIError(Exception):
    """Base class for API errors"""
    def __init__(
        self, 
        status_code: int, 
        detail: str, 
        error_code: Optional[str] = None
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        super().__init__(self.detail)


class TranscriptionError(APIError):
    """Error during transcription process"""
    def __init__(self, detail: str, error_code: Optional[str] = None):
        super().__init__(500, detail, error_code or "transcription_error")


class SummarizationError(APIError):
    """Error during summarization process"""
    def __init__(self, detail: str, error_code: Optional[str] = None):
        super().__init__(500, detail, error_code or "summarization_error")


class ResourceNotFoundError(APIError):
    """Resource not found error"""
    def __init__(self, detail: str, error_code: Optional[str] = None):
        super().__init__(404, detail, error_code or "not_found")


class InvalidRequestError(APIError):
    """Invalid request error"""
    def __init__(self, detail: str, error_code: Optional[str] = None):
        super().__init__(400, detail, error_code or "invalid_request")


class DatabaseError(APIError):
    """Database error"""
    def __init__(self, detail: str, error_code: Optional[str] = None):
        super().__init__(500, detail, error_code or "database_error")


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """
    Handler for API errors
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.detail
            }
        }
    )


def register_error_handlers(app):
    """
    Register error handlers for the application
    """
    app.add_exception_handler(APIError, api_error_handler)
