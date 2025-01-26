import re

import cv2
import numpy as np
import pytesseract
from PIL import UnidentifiedImageError

from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)


def extract_text_from_image_file(image_bytes: bytes) -> str:
    try:
        if not image_bytes:
            raise ValueError("Empty image data provided")

        image_np = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Invalid or unsupported image format")

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        extracted_text = pytesseract.image_to_string(image_rgb)
        LOGGER.debug(f"Extracted text: {extracted_text}")

        return extracted_text

    except UnidentifiedImageError as e:
        LOGGER.error(f"Unsupported image format: {e}")
        raise ValueError("Unsupported image format") from e
    except Exception as e:
        LOGGER.exception("Unexpected error during image processing")
        raise ValueError("Failed to process image") from e


def extract_numbers(text: str) -> str:
    """Extract only numeric characters from the OCR output."""
    numbers = re.findall(r"\d+", text)  # Extract all numbers
    return " ".join(numbers) if numbers else "No numbers found"
