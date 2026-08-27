from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class BBox(BaseModel):
    pageIndex: int = Field(..., ge=0, description="0-based page index")
    x: float = Field(..., ge=0, le=1)
    y: float = Field(..., ge=0, le=1)
    w: float = Field(..., gt=0, le=1)
    h: float = Field(..., gt=0, le=1)

class Question(BaseModel):
    id: str
    label: str  # e.g., "11"
    subLabel: Optional[str] = None  # e.g., "a"
    displayNumber: str  # e.g., "11 a." or "1"
    text: str
    order: int
    maxScore: Optional[float] = None
    pageHint: Optional[int] = None
    type: Optional[str] = None  # short, long, diagram

class AnswerRegion(BaseModel):
    id: str
    detectedLabel: Optional[str] = None
    textPreview: str
    blockIds: List[int] = []
    bboxes: List[BBox] = []
    pages: List[int] = []
    confidence: Optional[float] = None

class Mapping(BaseModel):
    questionId: str
    answerIds: List[str] = []
    status: Literal["answered", "unanswered", "orphan"]
    confidence: float = 0.0

class Grading(BaseModel):
    questionId: str
    score: float
    maxScore: float
    feedback: str
    isCorrect: Optional[bool] = None
    isUnanswered: bool = False

class Summary(BaseModel):
    totalScore: float
    maxTotal: float
    answered: int
    unanswered: int
    orphan: int
    overallFeedback: Optional[str] = None

class FileInfo(BaseModel):
    name: str
    pages: int
    mime: str
    size: int
    imagesUrl: List[str] = []  # /api/v1/sessions/{id}/file/{type}/{idx}

class Session(BaseModel):
    id: str
    status: str
    progress: int  # 0-100
    createdAt: datetime
    updatedAt: datetime
    files: dict  # {questionPaper: FileInfo, answerSheet: FileInfo}
    questions: List[Question] = []
    answers: List[AnswerRegion] = []
    mappings: List[Mapping] = []
    grading: List[Grading] = []
    summary: Optional[Summary] = None
    error: Optional[str] = None

class CreateSessionResponse(BaseModel):
    id: str
    status: str
    progress: int
    message: str = "Session created, processing started"

class HealthResponse(BaseModel):
    ok: bool = True
    version: str = "1.0.0"
    groqConfigured: bool
