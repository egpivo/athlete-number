from athlete_number.core.schemas import NumberExtractionResponse
from athlete_number.services.ocr import OCRService


async def initialize_ocr():
    """Initialize the OCR service asynchronously."""
    return await OCRService.get_instance()


def process_images_with_ocr(ocr_service, images: list):
    """Extract numbers from images using OCR."""
    extracted_numbers_list = ocr_service.extract_numbers_from_images(
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
