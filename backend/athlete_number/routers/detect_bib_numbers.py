import asyncio
import traceback
from typing import List

from athlete_number.core.schemas import DetectionResponse
from athlete_number.services.detection import DetectionService
from athlete_number.utils.logger import setup_logger
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image

LOGGER = setup_logger(__name__)

router = APIRouter(prefix="/detect", tags=["Digit Detection"])


@router.on_event("startup")
async def startup_event():
    """Initialize detection service on startup"""
    try:
        await DetectionService.get_instance()
    except Exception as e:
        error_trace = traceback.format_exc()
        LOGGER.error(f"❌ Startup failed: {e}\n{error_trace}")
        raise RuntimeError("Startup failed")


async def get_detection_service():
    """Dependency to get detection service instance"""
    try:
        return await DetectionService.get_instance()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Service unavailable")


@router.post(
    "/bibs",
    response_model=List[DetectionResponse],
    description=(
        "This endpoint processes multiple image files and detects athlete bib numbers using "
        "a YOLO-based model. The response includes detected bounding boxes, confidence scores, "
        "and metadata for each processed image."
    ),
    responses={
        200: {"description": "Successful detection"},
        400: {"description": "Invalid input or missing files"},
        500: {"description": "Internal processing error"},
        503: {"description": "Service unavailable"},
    },
)
async def detect_bib_numbers(
    files: List[UploadFile] = File(...),
    service: DetectionService = Depends(get_detection_service),
) -> List[DetectionResponse]:
    """
    Detect bib numbers in multiple uploaded images using the YOLO model.

    - Accepts multiple images.
    - Runs detection in parallel using `asyncio.gather()`.
    - Returns bounding boxes, confidence scores, and image metadata.
    """

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    try:
        LOGGER.info(f"Received {len(files)} images for detection.")

        images = [Image.open(file.file).convert("RGB") for file in files]
        filenames = [file.filename for file in files]

        start_time = asyncio.get_event_loop().time()
        detections_batch = await asyncio.to_thread(service.detector.detect, images)
        processing_time = asyncio.get_event_loop().time() - start_time

        results = []
        for filename, detections, img in zip(filenames, detections_batch, images):
            results.append(
                DetectionResponse(
                    filename=filename,
                    detections=detections,
                    metadata={
                        "width": img.width,
                        "height": img.height,
                        "model_version": service.detector.model_version,
                        "device": service.detector.device_type,
                        "processing_time": processing_time / len(files),
                    },
                )
            )
        return results

    except Exception as e:
        LOGGER.error(f"❌ Batch detection failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal processing error.")
