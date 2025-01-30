import asyncio

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from athlete_number.core.schemas import AthleteNumberResponse
from athlete_number.services.detection import DetectionService
from athlete_number.services.detection_orchestrator import DetectionOCRService
from athlete_number.utils.image_processor import ImageHandler
from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)

router = APIRouter(prefix="/extract", tags=["Athlete Number Extraction"])


@router.post(
    "/bib-number",
    response_model=AthleteNumberResponse,
    summary="Extract athlete number using YOLO detection and OCR",
)
async def extract_athlete_number(
    file: UploadFile,
    image_handler: ImageHandler = Depends(),
    orchestrator: DetectionOCRService = Depends(DetectionOCRService.get_instance),
) -> AthleteNumberResponse:
    """
    Combines YOLO detection and OCR verification:
    - YOLO identifies potential bib number regions
    - OCR extracts text from the detected bib regions
    - Returns structured results including detections, OCR results, and processing time
    """
    try:
        start_time = asyncio.get_event_loop().time()

        # Convert file to image
        image = await image_handler.validate_and_convert(file)

        # Process image through YOLO + OCR
        athlete_numbers = await orchestrator.process_image(image)

        # Calculate processing time
        processing_time = round(asyncio.get_event_loop().time() - start_time, 4)

        # Get model versions
        detection_service = await DetectionService.get_instance()

        # Ensure orchestrator attributes exist
        orchestrator.last_detections = getattr(orchestrator, "last_detections", [])
        orchestrator.last_ocr_results = getattr(orchestrator, "last_ocr_results", [])
        orchestrator.last_confidence_score = getattr(
            orchestrator, "last_confidence_score", 0.0
        )

        # Prepare structured response
        response_data = {
            "athlete_numbers": athlete_numbers,  # List of detected bib numbers
            "yolo_detections": orchestrator.last_detections,
            "ocr_results": orchestrator.last_ocr_results,
            "processing_time": processing_time,
            "confidence": orchestrator.last_confidence_score,
            "model_versions": {
                "detection": detection_service.detector.model_version,
                "ocr": "tesseract-v5.3.1",
            },
        }

        LOGGER.info(f"📦 Final API Response: {response_data}")

        return AthleteNumberResponse(**response_data)

    except Exception as e:
        LOGGER.error(f"❌ Athlete number extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Processing failed")
