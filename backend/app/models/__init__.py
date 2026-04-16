"""Pydantic models for API requests/responses."""
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.schema import ClarifyingQuestion, CurrentSchema


class QuestionRequest(BaseModel):
    """Request for generating clarifying questions"""
    nl_input: str
    file_context: Optional[str] = None
    request_id: Optional[str] = None


class QuestionResponse(BaseModel):
    """Response with clarifying questions."""

    status: str
    questions: List[ClarifyingQuestion] = Field(default_factory=list)
    request_id: Optional[str] = None


class DiagramRequest(BaseModel):
    """Request for generating Mermaid diagram"""
    nl_input: str
    questions_answers: str
    existing_schema: Optional[str] = None
    request_id: Optional[str] = None


class DiagramResponse(BaseModel):
    """Response with Mermaid diagram."""

    status: str
    mermaid: str
    current_schema: Optional[CurrentSchema] = None
    validation_notes: List[str] = Field(default_factory=list)
    request_id: Optional[str] = None


class SQLRequest(BaseModel):
    """Request for generating SQL"""
    mermaid_diagram: str
    dialect: str = "PostgreSQL"
    request_id: Optional[str] = None


class SQLResponse(BaseModel):
    """Response with SQL DDL."""

    status: str
    sql: str
    dialect: str
    validation_notes: List[str] = Field(default_factory=list)
    request_id: Optional[str] = None


class RefineRequest(BaseModel):
    """Request to refine existing schema."""

    current_mermaid: str
    user_request: str
    request_id: Optional[str] = None
