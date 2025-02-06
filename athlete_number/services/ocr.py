import re
from typing import List

import numpy as np
import pytesseract

from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)


def clean_ocr_output(text: str) -> str:
    """Cleans OCR output to remove misclassified characters."""
    text = text.replace(" ", "")
    text = re.sub(r"[^0-9a-zA-Z]", "", text)
    return text


def parse_numbers(texts: List[str]) -> List[str]:
    return [num for text in texts for num in re.findall(r"[0-9a-zA-Z]+", text)]


def extract_text_from_image(image: np.ndarray) -> str:
    """Extract text from an image using Tesseract with preprocessing."""
    try:
        extracted_text = pytesseract.image_to_string(image, config="--psm 7")
        results = parse_numbers([extracted_text])

        LOGGER.info(f"🔍 Tesseract OCR Output: {results}")
        return "".join(results)
    except Exception as e:
        LOGGER.exception(f"❌ Tesseract OCR failed to extract text - {e}.")
        return ""


class OCRService:
    _instance = None

    def __init__(self):
        if OCRService._instance is not None:
            raise RuntimeError(
                "OCRService is a singleton class. Use get_instance() instead."
            )

    @classmethod
    async def get_instance(cls):
        """Singleton pattern for OCR service."""
        if cls._instance is None:
            cls._instance = OCRService()
        return cls._instance

    @staticmethod
    def clean_numbers(text: str) -> str:
        numbers = re.findall(r"[0-9a-zA-Z]+", text)
        return "".join(numbers) if numbers else ""
