"""Schema generation routes."""
import logging
from fastapi import APIRouter, HTTPException
from app.services.gemini_service import gemini_service
from app.models import (
    QuestionRequest,
    DiagramRequest,
    SQLRequest,
    RefineRequest,
    QuestionResponse,
    DiagramResponse,
    SQLResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/questions", response_model=QuestionResponse)
async def generate_questions(request: QuestionRequest):
    """Generate clarifying questions."""
    try:
        questions = await gemini_service.generate_questions(
            nl_input=request.nl_input,
            file_context=request.file_context
        )
        
        return QuestionResponse(
            status="success",
            questions=questions,
            request_id=getattr(request, 'request_id', 'default')
        )
    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diagram", response_model=DiagramResponse)
async def generate_diagram(request: DiagramRequest):
    """Generate Chen-style Mermaid diagram."""
    try:
        mermaid_diagram, schema, validation_notes = await gemini_service.generate_mermaid(
            nl_input=request.nl_input,
            questions_answers=request.questions_answers,
            existing_schema=request.existing_schema
        )
        
        return DiagramResponse(
            status="success",
            mermaid=mermaid_diagram,
            current_schema=schema,
            validation_notes=validation_notes,
            request_id=getattr(request, 'request_id', 'default')
        )
    except Exception as e:
        logger.error(f"Error generating diagram: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sql", response_model=SQLResponse)
async def generate_sql(request: SQLRequest):
    """Generate SQL DDL."""
    try:
        sql, validation_notes = await gemini_service.generate_sql(
            mermaid_diagram=request.mermaid_diagram,
            dialect=request.dialect
        )
        
        return SQLResponse(
            status="success",
            sql=sql,
            dialect=request.dialect,
            validation_notes=validation_notes,
            request_id=getattr(request, 'request_id', 'default')
        )
    except Exception as e:
        logger.error(f"Error generating SQL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refine", response_model=DiagramResponse)
async def refine_schema(request: RefineRequest):
    """Refine existing schema."""
    try:
        refined_mermaid, schema, validation_notes = await gemini_service.refine_schema(
            current_mermaid=request.current_mermaid,
            user_request=request.user_request
        )
        
        return DiagramResponse(
            status="success",
            mermaid=refined_mermaid,
            current_schema=schema,
            validation_notes=validation_notes,
            request_id=getattr(request, 'request_id', 'default')
        )
    except Exception as e:
        logger.error(f"Error refining schema: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "schema-api"}
