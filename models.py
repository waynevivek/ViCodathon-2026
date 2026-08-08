from typing import List, Optional
from pydantic import BaseModel, Field


class CandidateMember(BaseModel):
    id: str
    name: str
    jobRole: Optional[str] = None
    yearsExperience: Optional[int] = None
    education: Optional[str] = None
    status: Optional[str] = None


class CandidateMission(BaseModel):
    day: int
    title: str
    passed: Optional[bool] = None
    attempts: Optional[int] = None
    skipped: Optional[bool] = None


class CandidateSignals(BaseModel):
    commitDays: Optional[int] = None
    missionsCompleted: Optional[int] = None
    missionsFirstTry: Optional[int] = None


class Candidate(BaseModel):
    member: CandidateMember
    missions: List[CandidateMission] = []
    signals: Optional[CandidateSignals] = None


class InterviewRequest(BaseModel):
    sessionId: str
    candidate: Optional[Candidate] = None
    message: Optional[str] = None


class Feedback(BaseModel):
    summary: str
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    next: List[str] = Field(default_factory=list)


class InterviewResponse(BaseModel):
    reply: str
    done: bool = False
    feedback: Optional[Feedback] = None
