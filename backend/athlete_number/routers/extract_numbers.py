from typing import List

import cv2
import numpy as np
from athlete_number.core.schemas import NumberExtractionResponse
from athlete_number.services.ocr import OCRService
from athlete_number.utils.logger import setup_logger
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from PIL import Image

LOGGER = setup_logger(__name__)
router = APIRouter()


@router.post(
    "/numbers",
    response_model=List[NumberExtractionResponse],
    summary="Extract numbers from multiple images using OCR",
    description="Processes uploaded image files to extract numbers using OCR.",
    responses={
        200: {"description": "Successfully extracted numbers"},
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

    ocr_service = await OCRService.get_instance()

    try:
        images = []
        filenames = []
        for file in files:
            image_bytes = await file.read()
            if not image_bytes:
                raise ValueError(f"File {file.filename} is empty or unreadable.")

            image_np = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError(
                    f"Failed to decode image {file.filename}, invalid format."
                )

            images.append(Image.fromarray(image))
            filenames.append(file.filename)

        extracted_numbers_list = ocr_service.extract_numbers_from_images(images)

        results = [
            NumberExtractionResponse(
                filename=filenames[i],
                extracted_number=extracted_numbers_list[i]
                if isinstance(extracted_numbers_list[i], list)
                else [extracted_numbers_list[i]],
            )
            for i in range(len(filenames))
        ]

        return results

    except ValueError as e:
        LOGGER.error(f"Error processing images: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        LOGGER.exception(f"Failed to process images: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OCR processing failed.",
        )
