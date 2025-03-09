from athlete_number.core.schemas import NumberExtractionResponse
from athlete_number.services.detection_orchestrator import DetectionOCRService
from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)

async def initialize_ocr():
    """Initialize the DetectionOCRService asynchronously."""
    return await DetectionOCRService.get_instance(yolo_gpus=[0], ocr_gpus=[1,2,3])


async def process_images_with_ocr(ocr_service, images: list, filenames: list):
    """Detect bib numbers using YOLO, then extract numbers using OCR."""
    extracted_numbers_list = await ocr_service.process_images(images)

    if len(extracted_numbers_list) != len(filenames):
        LOGGER.error(f"❌ Mismatch: {len(extracted_numbers_list)} results for {len(filenames)} filenames")
        return []

    results = [
        NumberExtractionResponse(
            filename=filename,
            extracted_number=extracted_numbers_list[i] if i < len(extracted_numbers_list) else [],
        )
        for i, filename in enumerate(filenames)
    ]
    return results
