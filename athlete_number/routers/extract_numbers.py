import re
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile

from athlete_number.core.schemas import NumberExtractionResponse
from athlete_number.services.ocr import extract_text_from_image_file
from athlete_number.utils.logger import setup_logger

router = APIRouter(prefix="/extract", tags=["OCR"])
LOGGER = setup_logger(__name__)


def parse_numbers(numbers: List[str]) -> List[str]:
    parsed_numbers = []
    for number in numbers:
        parsed_number = re.findall(r"\d+", number)
        if parsed_number:
            parsed_numbers.append("".join(parsed_number))
    return parsed_numbers


@router.post(
    "/numbers",
    summary="Upload an image file for numbers extraction",
    response_model=NumberExtractionResponse,
)
async def extract_text(file: UploadFile = File(...)) -> NumberExtractionResponse:
    try:
        image_bytes = await file.read()
        extracted_numbers = extract_text_from_image_file(image_bytes)
        extracted_number = parse_numbers(extracted_numbers)
        return NumberExtractionResponse(extracted_number=extracted_number)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        LOGGER.exception("Failed to process the uploaded file")
        raise HTTPException(status_code=500, detail="Internal server error")
