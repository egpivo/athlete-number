import asyncio
import traceback
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from athlete_number.core.schemas import DetectionResponse
from athlete_number.services.detection import DetectionService
from athlete_number.utils.image_processor import ImageHandler
from athlete_number.utils.logger import setup_logger

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
    files: List[UploadFile] = File(...),  # Accept multiple files
    service: DetectionService = Depends(get_detection_service),
    image_handler: ImageHandler = Depends(),
) -> List[DetectionResponse]:
    """
    Detect bib numbers in multiple uploaded images using the YOLO model.

    - Accepts multiple images.
    - Runs detection in parallel using `asyncio.gather()`.
    - Returns bounding boxes, confidence scores, and image metadata.
    """

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    async def process_file(file: UploadFile):
        try:
            LOGGER.info(f"Processing file: {file.filename}")

            image = await image_handler.validate_and_convert(file)
            start_time = asyncio.get_event_loop().time()
            detections = await asyncio.to_thread(service.detector.detect, image)
            processing_time = asyncio.get_event_loop().time() - start_time

            response = DetectionResponse(
                filename=file.filename,
                detections=detections,
                metadata={
                    "width": image.width,
                    "height": image.height,
                    "model_version": service.detector.model_version,
                    "device": service.detector.device_type,
                    "processing_time": processing_time,
                },
            )

            return response.model_dump()
        except Exception as e:
            LOGGER.error(
                f"Detection failed for {file.filename}: {str(e)}", exc_info=True
            )
            response = DetectionResponse(
                filename=file.filename,
                detections=[],
                metadata={"error": "Processing failed"},
            )
            return response.model_dump()

    results = await asyncio.gather(*(process_file(file) for file in files))

    return results
