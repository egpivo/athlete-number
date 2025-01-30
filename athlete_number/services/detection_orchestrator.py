import asyncio
from typing import List

import cv2
import numpy as np
from PIL import Image

from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)


def is_valid_bbox(bbox):
    """Filters out detections that don't match typical bib number dimensions."""
    x1, y1, x2, y2 = map(int, bbox)
    width = x2 - x1
    height = y2 - y1
    aspect_ratio = width / height

    # Bib numbers are usually wider than they are tall
    return 2.0 > aspect_ratio > 0.5


MIN_WIDTH = 150
MIN_HEIGHT = 100


def adjust_bbox(bbox, image_width, image_height):
    """Ensures the cropped region has a minimum width and height."""
    x1, y1, x2, y2 = map(int, bbox)

    width = x2 - x1
    height = y2 - y1

    # Ensure minimum width
    if width < MIN_WIDTH:
        center_x = (x1 + x2) // 2
        x1 = max(0, center_x - MIN_WIDTH // 2)
        x2 = min(image_width, center_x + MIN_WIDTH // 2)

    # Ensure minimum height
    if height < MIN_HEIGHT:
        center_y = (y1 + y2) // 2
        y1 = max(0, center_y - MIN_HEIGHT // 2)
        y2 = min(image_height, center_y + MIN_HEIGHT // 2)

    return x1, y1, x2, y2


def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """Prepares the image for OCR by increasing contrast and removing noise."""
    img_np = np.array(image)

    # Convert to grayscale
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Apply strong thresholding
    _, binarized = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return Image.fromarray(binarized)


import pytesseract


def extract_text_from_image(image: Image.Image) -> str:
    """Extracts text from image using optimized Tesseract settings."""
    return pytesseract.image_to_string(
        image, config="--psm 7 -c tessedit_char_whitelist=0123456789"
    )


class DetectionOCRService:
    _instance = None

    def __init__(self):
        self.detection_service = None
        self.ocr_service = None
        self.lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls):
        """Singleton pattern for the orchestrator service."""
        if cls._instance is None:
            cls._instance = DetectionOCRService()
            await cls._instance.initialize()
        return cls._instance

    async def initialize(self):
        """Initialize detection and OCR services."""
        async with self.lock:
            from athlete_number.services.detection import DetectionService
            from athlete_number.services.ocr import OCRService

            self.detection_service = await DetectionService.get_instance()
            self.ocr_service = await OCRService.get_instance()
            LOGGER.info("✅ DetectionOCRService initialized.")

    async def process_image(self, image: Image.Image) -> str:
        """Runs YOLO detection and OCR pipeline with improved preprocessing."""
        detections = await self.detection_service.detector.detect_async(image)

        if not detections:
            LOGGER.warning("⚠ No digits detected.")
            return ""

        filtered_detections = [d for d in detections if is_valid_bbox(d["bbox"])]

        if not filtered_detections:
            LOGGER.warning("⚠ All detections were filtered out.")
            return ""

        results = []
        image_width, image_height = image.size

        for idx, detection in enumerate(filtered_detections):
            try:
                bbox = adjust_bbox(detection["bbox"], image_width, image_height)
                cropped_img = image.crop(bbox)

                # Debug: Save cropped images
                debug_path = f"debug_crops/crop_{idx}.jpg"
                cropped_img.save(debug_path)
                LOGGER.info(f"📷 Saved cropped image: {debug_path} (BBox: {bbox})")

                # Apply OCR preprocessing
                cropped_img = preprocess_for_ocr(cropped_img)

                # Run optimized OCR
                raw_text = extract_text_from_image(cropped_img)
                clean_number = self.ocr_service.clean_numbers(raw_text)

                if clean_number:
                    results.append(
                        (clean_number, bbox[0])
                    )  # Store digit with X-coordinate
                else:
                    LOGGER.warning(f"⚠ Empty OCR result for bbox: {bbox}")

            except Exception as e:
                LOGGER.error(f"❌ Failed to process detection: {e}", exc_info=True)

        return self._concatenate_numbers(results)

    def _concatenate_numbers(self, results: List[tuple]) -> str:
        """Concatenates detected digits based on X-coordinates."""

        LOGGER.info(f"🔍 Inside _concatenate_numbers: {results} (type: {type(results)})")

        if not isinstance(results, list):
            LOGGER.error(
                f"❌ Expected a list but got {type(results)}. Check process_image()."
            )
            return ""

        if any(not isinstance(item, tuple) for item in results):
            LOGGER.error(f"❌ Expected list of tuples, but got: {results}")
            return ""

        digits = [digit for digit, _ in results if digit.strip().isdigit()]

        if not digits:
            LOGGER.warning("⚠ OCR detected only empty or invalid values.")
            return ""

        full_number = "".join(digits)

        LOGGER.info(f"🏅 Final athlete number: {full_number}")
        return full_number
