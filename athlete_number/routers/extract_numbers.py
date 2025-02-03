from typing import List

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from athlete_number.core.schemas import NumberExtractionResponse
from athlete_number.services.ocr import extract_text_from_image, parse_numbers
from athlete_number.utils.logger import setup_logger

router = APIRouter(prefix="/extract", tags=["OCR"])
LOGGER = setup_logger(__name__)


@router.post(
    "/numbers",
    response_model=List[NumberExtractionResponse],  # ✅ Supports batch responses
    summary="Extract numbers from multiple images using OCR",
    description=(
        "This endpoint processes multiple uploaded image files to extract numeric values "
        "using Optical Character Recognition (OCR). The response includes detected numbers, "
        "processing metadata, and filenames for reference."
    ),
    responses={
        200: {"description": "Successfully extracted numbers from images"},
        400: {"description": "Invalid input or missing files"},
        500: {"description": "Internal processing error"},
        503: {"description": "Service unavailable"},
    },
)
async def extract_text(
    files: List[UploadFile] = File(...),
) -> List[NumberExtractionResponse]:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded."
        )

    results = []

    for file in files:
        try:
            LOGGER.info(f"Processing file: {file.filename}")
            image_bytes = await file.read()

            if not image_bytes:
                LOGGER.warning(f"File {file.filename} is empty.")
                raise ValueError(f"File {file.filename} is empty or unreadable.")

            image_np = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Failed to decode the image, invalid format.")

            extracted_text = extract_text_from_image(image)
            extracted_numbers = parse_numbers(extracted_text)

            results.append(
                NumberExtractionResponse(
                    filename=file.filename, extracted_number=extracted_numbers
                )
            )

        except ValueError as e:
            LOGGER.error(f"Error processing {file.filename}: {str(e)}")
            results.append(
                NumberExtractionResponse(filename=file.filename, extracted_number=[])
            )
        except Exception as e:
            LOGGER.exception(f"Failed to process {file.filename}: {str(e)}")
            results.append(
                NumberExtractionResponse(filename=file.filename, extracted_number=[])
            )

    return results
