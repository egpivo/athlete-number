from fastapi import APIRouter, File, HTTPException, UploadFile

from athlete_number.core.schemas import TextExtractionResponse
from athlete_number.services.ocr import extract_text_from_image_file
from athlete_number.utils.logger import setup_logger

router = APIRouter(prefix="/extract", tags=["OCR"])
LOGGER = setup_logger(__name__)


@router.post(
    "/number",
    summary="Upload an image file for number extraction",
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
        LOGGER.exception("Failed to process the uploaded file")
        raise HTTPException(status_code=500, detail="Internal server error")
