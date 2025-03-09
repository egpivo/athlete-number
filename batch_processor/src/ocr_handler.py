from athlete_number.core.schemas import NumberExtractionResponse
from athlete_number.services.detection_orchestrator import DetectionOCRService


async def initialize_ocr():
    """Initialize the DetectionOCRService asynchronously."""
    return await DetectionOCRService.get_instance(yolo_gpus=[0,1], ocr_gpus=[2,3])


async def process_images_with_ocr(ocr_service, images: list, filenames: list):
    """Detect bib numbers using YOLO, then extract numbers using OCR."""
    extracted_numbers_list = await ocr_service.process_images(images)

    results = [
        NumberExtractionResponse(
            filename=filename,
            extracted_number=extracted_numbers_list[i]
            if isinstance(extracted_numbers_list[i], list)
            else [extracted_numbers_list[i]],
        )
        for i, filename in enumerate(filenames)
    ]
    return results
