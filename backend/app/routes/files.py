"""API routes for file upload and processing"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from app.models.schema import FileUploadResponse
from app.utils.file_processor import process_uploaded_file

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> FileUploadResponse:
    """Upload and process a file (PDF, CSV, TXT, DOCX)"""
    try:
        content = await file.read()
        extracted_text = await process_uploaded_file(content, file.filename)
        
        return FileUploadResponse(
            filename=file.filename,
            extracted_text=extracted_text,
            char_count=len(extracted_text)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
