"""API routes for chat and schema interactions."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.models.schema import ChatResponse
from app.services.gemini_service import gemini_service
from app.services.session_manager import session_store

router = APIRouter(prefix="/api/chat", tags=["chat"])


class InitialInputRequest(BaseModel):
    """Initial NL input and optional file context."""

    input_text: Optional[str] = None
    file_context: Optional[str] = None


class ConfirmSchemaRequest(BaseModel):
    """Confirm schema and generate Mermaid."""

    session_id: str
    answers_summary: str


class RefineSchemaRequest(BaseModel):
    """Request to refine existing schema."""

    session_id: str
    refinement_request: str


class SQLGenerationRequest(BaseModel):
    """Request SQL generation."""

    session_id: str
    dialect: str = "PostgreSQL"


@router.post("/init")
async def initialize_session(request: InitialInputRequest) -> dict:
    """Initialize a session and generate clarifying questions."""

    try:
        effective_input = (request.input_text or "").strip()
        effective_file_context = (request.file_context or "").strip() or None

        session_id = session_store.create_session(effective_input, effective_file_context)

        questions = await gemini_service.generate_questions(
            effective_input,
            effective_file_context,
        )
        session_store.set_questions(session_id, questions)

        display_input = effective_input or effective_file_context or "No text or file provided. Using a generic schema scaffold."
        session_store.add_to_chat_history(session_id, "user", display_input)
        session_store.add_to_chat_history(
            session_id,
            "assistant",
            "\n".join([f"{question.id}. {question.question}" for question in questions]),
        )

        return {
            "session_id": session_id,
            "questions": questions,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating questions: {str(e)}")


@router.post("/confirm-answers")
async def confirm_answers(request: ConfirmSchemaRequest) -> ChatResponse:
    """Confirm answers and generate Mermaid diagram."""

    session = session_store.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        session_store.add_to_chat_history(request.session_id, "user", request.answers_summary)

        mermaid, schema, validation_notes = await gemini_service.generate_mermaid(
            session.nl_input,
            request.answers_summary,
            session.mermaid_diagram,
            session.file_context,
        )

        session_store.update_session(
            request.session_id,
            {
                "mermaid_diagram": mermaid,
                "current_schema": schema,
            },
        )

        session_store.add_to_chat_history(request.session_id, "assistant", mermaid)

        return ChatResponse(
            content="Chen ER diagram generated successfully!",
            type="mermaid",
            mermaid_diagram=mermaid,
            updated_schema=schema,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Mermaid: {str(e)}")


@router.post("/refine")
async def refine_schema(request: RefineSchemaRequest) -> ChatResponse:
    """Refine existing schema."""

    session = session_store.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.mermaid_diagram:
        raise HTTPException(status_code=400, detail="No schema to refine")

    try:
        session_store.add_to_chat_history(request.session_id, "user", request.refinement_request)

        refined_mermaid, refined_schema, validation_notes = await gemini_service.refine_schema(
            session.mermaid_diagram,
            request.refinement_request,
        )

        session_store.update_session(
            request.session_id,
            {
                "mermaid_diagram": refined_mermaid.strip(),
                "current_schema": refined_schema,
            },
        )

        session_store.add_to_chat_history(request.session_id, "assistant", refined_mermaid)

        return ChatResponse(
            content="Schema refined successfully!",
            type="refinement",
            mermaid_diagram=refined_mermaid.strip(),
            updated_schema=refined_schema,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refining schema: {str(e)}")


@router.post("/generate-sql")
async def generate_sql(request: SQLGenerationRequest) -> ChatResponse:
    """Generate SQL from current schema."""

    session = session_store.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.mermaid_diagram:
        raise HTTPException(status_code=400, detail="No schema available")

    try:
        sql_code, validation_notes = await gemini_service.generate_sql(
            session.mermaid_diagram,
            request.dialect,
        )

        session_store.add_to_chat_history(request.session_id, "assistant", sql_code)

        return ChatResponse(
            content=sql_code.strip(),
            type="sql",
            updated_schema=session.current_schema,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating SQL: {str(e)}")


@router.get("/session/{session_id}")
async def get_session(session_id: str) -> dict:
    """Get session details."""

    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "nl_input": session.nl_input,
        "file_context": session.file_context,
        "clarifying_questions": session.clarifying_questions,
        "current_schema": session.current_schema,
        "mermaid_diagram": session.mermaid_diagram,
        "chat_history": session.chat_history,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }
