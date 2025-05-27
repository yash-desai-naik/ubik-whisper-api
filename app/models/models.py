from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class StatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class HealthResponse(BaseModel):
    status: str = "ok"


class TranscribeRequest(BaseModel):
    file_path: str


class TranscribeResponse(BaseModel):
    id: str
    status: StatusEnum = StatusEnum.PENDING
    progress: float = 0
    transcription: Optional[str] = None
    error: Optional[str] = None


class TranscribeStatusResponse(BaseModel):
    id: str
    status: StatusEnum
    progress: float
    transcription: Optional[str] = None
    error: Optional[str] = None


class SummarizeRequest(BaseModel):
    transcribe_id: str


class SummarizeResponse(BaseModel):
    id: str
    status: StatusEnum = StatusEnum.PENDING
    progress: float = 0
    summary: Optional[str] = None
    error: Optional[str] = None


class SummarizeStatusResponse(BaseModel):
    id: str
    status: StatusEnum
    progress: float
    summary: Optional[str] = None
    error: Optional[str] = None


class ChunkInfo(BaseModel):
    start_time: float
    end_time: float
    text: str


class TranscriptionData(BaseModel):
    id: str
    status: StatusEnum
    progress: float
    chunks: List[ChunkInfo] = []
    full_transcription: Optional[str] = None
    error: Optional[str] = None


class SummaryData(BaseModel):
    id: str
    transcribe_id: str
    status: StatusEnum
    progress: float
    summary: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None
