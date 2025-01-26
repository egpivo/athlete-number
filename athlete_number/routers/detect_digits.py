import asyncio
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from athlete_number.core.configs import YOLOv5_URL
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
        await DetectionService.get_instance(YOLOv5_URL)
    except Exception as e:
        LOGGER.error(f"Startup failed: {str(e)}")
        raise RuntimeError("Startup failed")


async def get_detection_service():
    """Dependency to get detection service instance"""
    try:
        return await DetectionService.get_instance(YOLOv5_URL)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Service unavailable")


@router.post(
    "/detect",
    response_model=DetectionResponse,
    responses={
        200: {"description": "Successful detection"},
        400: {"description": "Invalid input"},
        500: {"description": "Internal processing error"},
        503: {"description": "Service unavailable"},
    },
)
async def detect_digits(
    file: UploadFile,
    service: DetectionService = Depends(get_detection_service),
    image_handler: ImageHandler = Depends(),
) -> DetectionResponse:
    """
    Detect digits in the uploaded image using the YOLO model.
    Returns detection results and basic metadata.
    """
    try:
        # Process image asynchronously
        image = await image_handler.validate_and_convert(file)

        # Start time
        start_time = asyncio.get_event_loop().time()

        # Run detection in thread pool to avoid blocking
        detections = await asyncio.to_thread(service.detector.detect, image)

        # End time
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time

        return DetectionResponse(
            detections=detections,
            metadata={
                "width": image.width,
                "height": image.height,
                "model_version": service.detector.model_version,
                "device": service.detector.device_type,
                "processing_time": processing_time,
            },
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        LOGGER.error(f"Detection failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal processing error")


@router.get("/health")
async def service_health(
    service: DetectionService = Depends(get_detection_service),
) -> Dict[str, str]:
    """
    Health-check endpoint to confirm service readiness.
    """
    return {
        "status": "healthy" if service.detector else "unavailable",
        "model_version": service.detector.model_version
        if service.detector
        else "unknown",
        "device": service.detector.device_type if service.detector else "unknown",
        "model_status": "loaded" if service.detector else "failed",
    }
