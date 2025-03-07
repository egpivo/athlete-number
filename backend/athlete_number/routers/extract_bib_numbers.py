import asyncio
import os
from typing import List

import cv2
import numpy as np
import torch
from athlete_number.core.schemas import AthleteNumberResponse
from athlete_number.services.detection_orchestrator import DetectionOCRService
from athlete_number.utils.logger import setup_logger
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

LOGGER = setup_logger(__name__)
router = APIRouter(prefix="/extract", tags=["Athlete Number Extraction"])

# Read batch size from environment variable, default to 2 if not set
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 2))


def load_image_from_upload(file: UploadFile) -> np.ndarray:
    """Load an image from an UploadFile object into a NumPy array."""
    image_bytes = file.file.read()
    image_np = np.frombuffer(image_bytes, np.uint8)  # Convert bytes to NumPy array
    return cv2.imdecode(image_np, cv2.IMREAD_COLOR)  # Decode image


@router.post(
    "/bib-numbers",
    response_model=List[AthleteNumberResponse],
    summary="Extract athlete numbers from multiple images using YOLO and OCR",
    description="Processes multiple uploaded images to detect and extract bib numbers.",
    responses={
        200: {"description": "Successfully extracted bib numbers"},
        400: {"description": "Invalid input or missing files"},
        500: {"description": "Internal processing error"},
        503: {"description": "Service unavailable"},
    },
)
async def extract_athlete_numbers(
    files: List[UploadFile] = File(...),
    orchestrator: DetectionOCRService = Depends(DetectionOCRService.get_instance),
) -> List[AthleteNumberResponse]:
    """
    ### **Batch Athlete Number Extraction API**
    - **Step 1**: YOLO detects bib numbers in batch.
    - **Step 2**: GOT-OCR-2.0 extracts text asynchronously.
    - **Step 3**: Returns results including detected numbers, bounding boxes, and processing time.
    """

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    LOGGER.info(
        f"Received {len(files)} images for batch processing (Batch Size: {BATCH_SIZE})."
    )

    # Load images into memory
    images = [load_image_from_upload(file) for file in files]
    filenames = [file.filename for file in files]

    responses = []

    # Process in Batches
    for i in range(0, len(filenames), BATCH_SIZE):
        batch_images = images[i : i + BATCH_SIZE]
        batch_filenames = filenames[i : i + BATCH_SIZE]

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        try:
            start_time = asyncio.get_event_loop().time()

            extracted_numbers_batch = await orchestrator.process_images(batch_images)
            processing_time = round(asyncio.get_event_loop().time() - start_time, 4)

            for filename, extracted_numbers in zip(
                batch_filenames, extracted_numbers_batch
            ):
                response_data = {
                    "filename": filename,
                    "athlete_numbers": extracted_numbers,
                    "processing_time": processing_time / len(batch_filenames),
                    "model_versions": {
                        "detection": orchestrator.detection_service.detector.model_version,
                        "ocr": "GOT-OCR-2.0",
                    },
                }

                LOGGER.debug(f"📦 Processed {filename}: {response_data}")

                responses.append(
                    AthleteNumberResponse(
                        filename=response_data["filename"],
                        athlete_numbers=extracted_numbers
                        if isinstance(extracted_numbers, list)
                        else [extracted_numbers],
                    )
                )

        except torch.cuda.OutOfMemoryError:
            LOGGER.error("🔥 CUDA Out of Memory! Reducing batch size may help.")
            torch.cuda.empty_cache()
            raise HTTPException(
                status_code=500,
                detail="GPU out of memory. Try processing fewer images.",
            )

    return responses
