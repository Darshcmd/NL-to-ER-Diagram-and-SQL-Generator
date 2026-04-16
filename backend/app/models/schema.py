from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SchemaAttribute(BaseModel):
    """A single ER diagram attribute / SQL column."""

    name: str
    type: str = "string"
    pk: bool = False
    fk: bool = False
    nullable: bool = True
    unique: bool = False
    default: Optional[str] = None
    note: Optional[str] = None


class SchemaEntity(BaseModel):
    """A logical entity in the generated schema."""

    name: str
    label: Optional[str] = None
    attributes: List[SchemaAttribute] = Field(default_factory=list)
    description: Optional[str] = None


class SchemaRelationship(BaseModel):
    """A relationship between two entities."""

    from_entity: str
    to_entity: str
    cardinality: str  # "1:1", "1:N", "M:N"
    label: str
    reverse_label: Optional[str] = None
    bridge_entity: Optional[str] = None


class CurrentSchema(BaseModel):
    """The current working schema for a session."""

    domain: str = "generic"
    summary: str = ""
    entities: List[SchemaEntity] = Field(default_factory=list)
    relationships: List[SchemaRelationship] = Field(default_factory=list)
    validation_notes: List[str] = Field(default_factory=list)
    sample_data: Dict[str, List[Dict[str, object]]] = Field(default_factory=dict)


class ClarifyingQuestion(BaseModel):
    """Structured clarifying question shown to the user."""

    id: str
    question: str
    focus: str
    example_answer: Optional[str] = None


class SessionState(BaseModel):
    """Complete session state for a user."""

    session_id: str
    nl_input: str
    file_context: Optional[str] = None
    clarifying_questions: List[ClarifyingQuestion] = Field(default_factory=list)
    current_schema: CurrentSchema = Field(default_factory=CurrentSchema)
    mermaid_diagram: Optional[str] = None
    chat_history: List[Dict[str, str]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatMessage(BaseModel):
    """Chat message from user."""

    content: str
    type: str  # "question_answer", "refinement_request", "sql_generation"


class ChatResponse(BaseModel):
    """Chat response from assistant."""

    content: str
    type: str  # "questions", "mermaid", "confirmation", "sql", "refinement"
    updated_schema: Optional[CurrentSchema] = None
    mermaid_diagram: Optional[str] = None


class FileUploadResponse(BaseModel):
    """Response after file upload."""

    filename: str
    extracted_text: str
    char_count: int
