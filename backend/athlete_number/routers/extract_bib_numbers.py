import asyncio
from typing import List

from athlete_number.core.schemas import AthleteNumberResponse
from athlete_number.services.detection import DetectionService
from athlete_number.services.detection_orchestrator import DetectionOCRService
from athlete_number.utils.logger import setup_logger
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image

LOGGER = setup_logger(__name__)
router = APIRouter(prefix="/extract", tags=["Athlete Number Extraction"])


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
    detection_service: DetectionService = Depends(DetectionService.get_instance),
) -> List[AthleteNumberResponse]:
    """
    ### **Batch Athlete Number Extraction API**
    - **Step 1**: YOLO detects bib numbers in batch.
    - **Step 2**: GOT-OCR-2.0 extracts text asynchronously.
    - **Step 3**: Returns results including detected numbers, bounding boxes, and processing time.
    """

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    LOGGER.info(f"Received {len(files)} images for batch processing.")

    # Load images into memory
    images = [Image.open(file.file).convert("RGB") for file in files]
    filenames = [file.filename for file in files]

    start_time = asyncio.get_event_loop().time()
    detections_batch = await asyncio.to_thread(
        detection_service.detector.detect, images
    )
    extracted_numbers_batch = await orchestrator.process_images(images)
    processing_time = round(asyncio.get_event_loop().time() - start_time, 4)

    responses = []
    for filename, detections, extracted_numbers, img in zip(
        filenames, detections_batch, extracted_numbers_batch, images
    ):
        response_data = {
            "filename": filename,
            "athlete_numbers": extracted_numbers,
            "yolo_detections": detections,
            "processing_time": processing_time / len(files),
            "confidence": orchestrator.last_confidence_scores,
            "model_versions": {
                "detection": detection_service.detector.model_version,
                "ocr": "GOT-OCR-2.0",
            },
        }

        LOGGER.debug(f"📦 Processed {filename}: {response_data}")

        responses.append(
            AthleteNumberResponse(
                filename=response_data["filename"],
                athlete_numbers=response_data["athlete_numbers"],
            )
        )

    return responses
