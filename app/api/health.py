from fastapi import APIRouter
from app.models.models import HealthResponse

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check if the API is running
    """
    return HealthResponse(status="ok")
