from athlete_number.core.schemas import NumberExtractionResponse
from athlete_number.services.detection_orchestrator import DetectionOCRService


async def initialize_ocr():
    """Initialize the DetectionOCRService asynchronously."""
    return await DetectionOCRService.get_instance()


async def process_images_with_ocr(ocr_service, images: list):
    """Detect bib numbers using YOLO, then extract numbers using OCR."""
    extracted_numbers_list = await ocr_service.process_images(
        [img for img, _ in images]
    )

    results = [
        NumberExtractionResponse(
            filename=name,
            extracted_number=extracted_numbers_list[i]
            if isinstance(extracted_numbers_list[i], list)
            else [extracted_numbers_list[i]],
        )
        for i, (_, name) in enumerate(images)
    ]
    return results
