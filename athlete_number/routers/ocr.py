from fastapi import APIRouter, File, HTTPException, UploadFile

from athlete_number.core.schemas import TextExtractionResponse
from athlete_number.services.ocr_service import extract_text_from_image_file
from athlete_number.utils.logger import logger

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post(
    "/extract-text",
    summary="Upload an image file for text extraction",
    response_model=TextExtractionResponse,
)
async def extract_text(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        extracted_text = extract_text_from_image_file(image_bytes)
        return {"extracted_text": extracted_text}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Failed to process the uploaded file")
        raise HTTPException(status_code=500, detail="Internal server error")
