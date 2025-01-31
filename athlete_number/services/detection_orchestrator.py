import asyncio
import time
from typing import List

import cv2
import numpy as np
import pytesseract
from PIL import Image

from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)

# Minimum acceptable width and height for bounding boxes
MIN_WIDTH = 150
MIN_HEIGHT = 100


def is_valid_bbox(bbox):
    """Filters detections based on bounding box size and aspect ratio."""
    x1, y1, x2, y2 = map(int, bbox)
    width = x2 - x1
    height = y2 - y1
    aspect_ratio = width / height

    LOGGER.info(
        f"🔍 Checking BBox {bbox} - Width: {width}, Height: {height}, Aspect Ratio: {aspect_ratio}"
    )

    # Allow all detections for now, can refine later
    return True


def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """Prepares the image for OCR with minimal processing."""
    img_np = np.array(image)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    return Image.fromarray(gray)


def extract_text_from_image(image: Image.Image) -> str:
    """Extracts text from image using OCR."""
    text = pytesseract.image_to_string(image, config="--psm 7")
    LOGGER.info(f"📌 OCR Raw Output: {text.strip()}")
    return text.strip()


class DetectionOCRService:
    _instance = None

    def __init__(self):
        self.detection_service = None
        self.ocr_service = None
        self.lock = asyncio.Lock()

        # Store intermediate results for API responses
        self.last_detections = []
        self.last_ocr_results = []
        self.last_confidence_score = 0.0

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

    async def process_image(self, image: Image.Image) -> List[str]:
        """Runs YOLO detection and OCR pipeline with improved preprocessing."""
        start_time = time.time()
        detections = await self.detection_service.detector.detect_async(image)

        if not detections:
            LOGGER.warning("⚠ No bib numbers detected.")
            return []

        # Apply bbox validation
        filtered_detections = [d for d in detections if is_valid_bbox(d["bbox"])]

        if not filtered_detections:
            LOGGER.warning("⚠ All detections were filtered out.")
            return []

        results = []
        confidence_scores = []
        image_width, image_height = image.size

        self.last_detections = filtered_detections  # Store detections for API response
        self.last_ocr_results = []

        for idx, detection in enumerate(filtered_detections):
            try:
                bbox = detection["bbox"]
                confidence_scores.append(detection["confidence"])  # Store confidence

                cropped_img = image.crop(bbox)

                # Save cropped images for debugging
                raw_debug_path = f"debug_crops/raw_crop_{idx}.jpg"
                cropped_img.save(raw_debug_path)
                LOGGER.info(
                    f"📷 Saved raw cropped image: {raw_debug_path} (BBox: {bbox})"
                )

                # Apply OCR preprocessing
                processed_img = preprocess_for_ocr(cropped_img)

                # Save preprocessed image
                processed_debug_path = f"debug_crops/processed_crop_{idx}.jpg"
                processed_img.save(processed_debug_path)
                LOGGER.info(f"📷 Saved processed image: {processed_debug_path}")

                # Run OCR
                raw_text = extract_text_from_image(processed_img)
                clean_number = self.ocr_service.clean_numbers(raw_text)

                if clean_number:
                    results.append(clean_number)
                    self.last_ocr_results.append(clean_number)
                else:
                    LOGGER.warning(f"⚠ Empty OCR result for bbox: {bbox}")

            except Exception as e:
                LOGGER.error(f"❌ Failed to process detection: {e}", exc_info=True)

        self.last_confidence_score = (
            round(sum(confidence_scores) / len(confidence_scores), 4)
            if confidence_scores
            else 0.0
        )
        processing_time = round(time.time() - start_time, 4)

        LOGGER.info(
            f"🏅 Final Detected Athlete Numbers: {results} (Processing Time: {processing_time}s, Confidence: {self.last_confidence_score})"
        )

        return results  # Return list of detected bib numbers
