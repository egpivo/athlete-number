import re

from fastapi import APIRouter, File, HTTPException, UploadFile

from athlete_number.core.schemas import NumberExtractionResponse
from athlete_number.services.ocr import extract_text_from_image_file
from athlete_number.utils.logger import setup_logger

router = APIRouter(prefix="/extract", tags=["OCR"])
LOGGER = setup_logger(__name__)


def extract_numbers(text: str) -> str:
    """Extract only numeric characters from the OCR output."""
    numbers = re.findall(r"\d+", text)  # Extract all numbers
    return " ".join(numbers) if numbers else "No numbers found"


@router.post(
    "/number",
    summary="Upload an image file for number extraction",
    response_model=NumberExtractionResponse,
)
async def extract_text(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        extracted_text = extract_text_from_image_file(image_bytes)
        extracted_number = extract_numbers(extracted_text)
        return {"extracted_number": extracted_number}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        LOGGER.exception("Failed to process the uploaded file")
        raise HTTPException(status_code=500, detail="Internal server error")
