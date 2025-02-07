import asyncio
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from athlete_number.core.schemas import AthleteNumberResponse
from athlete_number.services.detection import DetectionService
from athlete_number.services.detection_orchestrator import DetectionOCRService
from athlete_number.utils.image_processor import ImageHandler
from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)

router = APIRouter(prefix="/extract", tags=["Athlete Number Extraction"])


@router.post(
    "/bib-numbers",
    response_model=List[AthleteNumberResponse],
    summary="Extract athlete numbers from multiple images using YOLO and OCR",
    description=(
        "This endpoint processes multiple uploaded image files to detect athlete bib numbers. "
        "It first identifies bib regions using a YOLO-based object detection model, "
        "then extracts the numbers using OCR (Optical Character Recognition). "
        "The response includes detected bib numbers, YOLO detection metadata, and processing time."
    ),
    responses={
        200: {"description": "Successfully extracted bib numbers"},
        400: {"description": "Invalid input or missing files"},
        500: {"description": "Internal processing error"},
        503: {"description": "Service unavailable"},
    },
)
async def extract_athlete_numbers(
    files: List[UploadFile] = File(...),  # Accept multiple files
    image_handler: ImageHandler = Depends(),
    orchestrator: DetectionOCRService = Depends(DetectionOCRService.get_instance),
) -> List[AthleteNumberResponse]:
    """
    ### **Batch Athlete Number Extraction API**

    **Process Flow:**
    - **Step 1**: YOLO detects potential bib number regions for each uploaded image.
    - **Step 2**: GOT-OCR-2.0 extracts text from the detected bib regions.
    - **Step 3**: Returns structured results, including:
      - Detected bib numbers
      - YOLO detection bounding boxes
      - OCR-extracted text
      - Processing time per image

    **Features:**
    - 🚀 **Batch Support**: Process multiple images at once.
    - 🎯 **Optimized Performance**: Runs asynchronously using `asyncio.gather()`.
    - 📊 **Detailed Metadata**: Includes detection confidence scores, processing time, and model version.

    **Example Response:**
    ```json
    [
        {
            "filename": "image1.jpg",
            "athlete_numbers": ["12345"],
        },
        {
            "filename": "image2.jpg",
            "athlete_numbers": ["67890"],
        }
    ]
    ```

    **Notes:**
    - The **OCR model (GOT-OCR-2.0)** extracts both **alphanumeric values**.
    - The **YOLO model** detects bib numbers with bounding boxes and confidence scores.
    - If an image fails processing, it will return an empty `"athlete_numbers": []`.

    **Status Codes:**
    - ✅ **200** - Successfully processed images.
    - ⚠️ **400** - Missing or invalid files.
    - ❌ **500** - Internal processing failure.
    - 🚧 **503** - Service unavailable.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    responses = []

    async def process_single_file(file: UploadFile):
        """Processes a single image file asynchronously."""
        try:
            start_time = asyncio.get_event_loop().time()

            image = await image_handler.validate_and_convert(file)

            athlete_numbers = await orchestrator.process_image(image)

            processing_time = round(asyncio.get_event_loop().time() - start_time, 4)
            detection_service = await DetectionService.get_instance()

            orchestrator.last_detections = getattr(orchestrator, "last_detections", [])
            orchestrator.last_ocr_results = getattr(
                orchestrator, "last_ocr_results", []
            )
            orchestrator.last_confidence_score = getattr(
                orchestrator, "last_confidence_score", 0.0
            )

            response_data = {
                "filename": file.filename,
                "athlete_numbers": athlete_numbers,
                "yolo_detections": orchestrator.last_detections,
                "ocr_results": orchestrator.last_ocr_results,
                "processing_time": processing_time,
                "confidence": orchestrator.last_confidence_score,
                "model_versions": {
                    "detection": detection_service.detector.model_version,
                    "ocr": "GOT-OCR-2.0",
                },
            }

            LOGGER.debug(f"📦 Processed {file.filename}: {response_data}")

            return AthleteNumberResponse(
                filename=response_data["filename"],
                athlete_numbers=response_data["athlete_numbers"],
            )

        except Exception as e:
            LOGGER.error(f"❌ Failed processing {file.filename}: {e}", exc_info=True)
            return AthleteNumberResponse(filename=file.filename, athlete_numbers=[])

    responses = await asyncio.gather(*(process_single_file(file) for file in files))

    return responses
