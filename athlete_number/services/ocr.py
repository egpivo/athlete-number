import asyncio
import re

import cv2
import easyocr
import numpy as np
import pytesseract
from PIL import Image

from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)

# Initialize EasyOCR Reader
reader = easyocr.Reader(["en"], gpu=True)


def preprocess_for_ocr(image: np.ndarray, debug_path: str) -> np.ndarray:
    """Preprocess the image for improved OCR accuracy."""

    if image is None or image.size == 0:
        raise ValueError("Invalid image received for OCR processing.")

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # CLAHE (Adaptive contrast enhancement)
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Adaptive Thresholding - Further fine-tuning
    binarized = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 10
    )

    # Morphological transformations to bolden digits
    kernel = np.ones((2, 2), np.uint8)
    dilated = cv2.dilate(binarized, kernel, iterations=1)

    # Resize for better OCR performance
    height, width = dilated.shape
    scale_factor = 800 / width
    resized = cv2.resize(dilated, (800, int(height * scale_factor)))

    # Save for debugging
    cv2.imwrite(f"{debug_path}_gray.jpg", gray)
    cv2.imwrite(f"{debug_path}_enhanced.jpg", enhanced)
    cv2.imwrite(f"{debug_path}_binarized.jpg", binarized)
    cv2.imwrite(f"{debug_path}_dilated.jpg", dilated)
    cv2.imwrite(f"{debug_path}_resized.jpg", resized)

    LOGGER.info(
        f"✅ Preprocessed image saved: {debug_path}_resized.jpg (Shape: {resized.shape})"
    )
    return resized


def clean_ocr_output(text: str) -> str:
    """Cleans OCR output to remove misclassified characters."""
    text = text.replace(" ", "")  # Remove spaces
    text = re.sub(r"[^0-9]", "", text)  # Keep only digits
    return text


def extract_text_from_image_file(
    image_bytes: bytes, debug_path: str = "debug_ocr"
) -> str:
    """Extract text from an image using EasyOCR and clean the results."""
    try:
        # Decode image bytes
        image_np = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Failed to decode the image, invalid format.")

        # Preprocess image
        processed_image = preprocess_for_ocr(image, debug_path)

        # Try EasyOCR first
        results = reader.readtext(processed_image, detail=0, allowlist="0123456789")

        if results:
            raw_text = "".join(results)
            cleaned_text = clean_ocr_output(raw_text)
            LOGGER.info(f"🔍 EasyOCR Output: {results} -> Cleaned: {cleaned_text}")
            return cleaned_text

        # If EasyOCR fails, use Tesseract as a fallback
        LOGGER.warning("⚠ EasyOCR failed, switching to Tesseract OCR.")
        tesseract_output = pytesseract.image_to_string(
            processed_image, config="--psm 6 -c tessedit_char_whitelist=0123456789"
        ).strip()

        cleaned_text = clean_ocr_output(tesseract_output)
        LOGGER.info(
            f"🔍 Tesseract Output: {tesseract_output} -> Cleaned: {cleaned_text}"
        )
        return cleaned_text

    except Exception:
        LOGGER.exception("❌ OCR failed to extract text.")
        return ""


def extract_text_from_image_file(
    image_bytes: bytes, debug_path: str = "debug_ocr"
) -> str:
    """Extract text from an image using EasyOCR with preprocessing."""
    try:
        # Decode image bytes
        image_np = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(
            image_np, cv2.IMREAD_COLOR
        )  # Ensure it's always a valid image

        if image is None:
            raise ValueError("Failed to decode the image, invalid format.")

        # Preprocess the image
        processed_image = preprocess_for_ocr(image, debug_path)

        # Run EasyOCR
        results = reader.readtext(processed_image, detail=0, allowlist="0123456789")

        LOGGER.info(f"🔍 EasyOCR Output: {results}")
        return "".join(results)  # Join all detected numbers
    except Exception:
        LOGGER.exception("❌ EasyOCR failed to extract text.")
        return ""


def extract_numbers(text: str) -> str:
    """Extract only numeric characters from the OCR output."""
    numbers = re.findall(r"\d+", text)  # Extract all numbers
    return " ".join(numbers) if numbers else "No numbers found"


class OCRService:
    _instance = None

    def __init__(self):
        pass

    @classmethod
    async def get_instance(cls):
        """Singleton pattern for OCR service."""
        if cls._instance is None:
            cls._instance = OCRService()
        return cls._instance

    async def extract_text_async(self, image: Image.Image) -> str:
        """Asynchronous OCR processing for an image."""
        return await asyncio.to_thread(self.extract_text, image)

    def extract_text(self, image: Image.Image) -> str:
        """Run OCR on an image."""
        try:
            image_np = np.array(image)
            image_rgb = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            extracted_text = pytesseract.image_to_string(image_rgb)
            LOGGER.debug(f"🔍 OCR Output: {extracted_text}")
            return extracted_text.strip()
        except Exception as e:
            LOGGER.error(f"❌ OCR processing failed: {e}", exc_info=True)
            return ""

    def clean_numbers(self, text: str) -> str:
        """Extract only numeric characters from OCR output."""
        numbers = re.findall(r"\d+", text)
        return "".join(numbers) if numbers else ""
