import asyncio
import os
import time
from typing import List

from PIL import Image

from athlete_number.services.ocr import OCRService
from athlete_number.services.utils import is_valid_bbox
from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)

MIN_CONFIDENCE = 0.7


class DetectionOCRService:
    _instance = None
    _debug_path = "debug_crops"

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

            self.detection_service = await DetectionService.get_instance()
            self.ocr_service = await OCRService.get_instance()
            LOGGER.info("✅ DetectionOCRService initialized.")

    async def process_image(
        self, image: Image.Image, is_debug: bool = False
    ) -> List[str]:
        """Runs YOLO detection and OCR pipeline with improved preprocessing."""
        start_time = time.time()
        detections = await self.detection_service.detector.detect_async(image)

        if not detections:
            LOGGER.warning("⚠ No bib numbers detected.")
            return []

        # Apply bbox validation and confidence screening
        filtered_detections = [
            d
            for d in detections
            if is_valid_bbox(d["bbox"]) and d["confidence"] >= MIN_CONFIDENCE
        ]

        if not filtered_detections:
            LOGGER.warning("⚠ All detections were filtered out.")
            return []

        results = []
        confidence_scores = []

        self.last_detections = filtered_detections
        self.last_ocr_results = []

        for idx, detection in enumerate(filtered_detections):
            try:
                bbox = detection["bbox"]
                confidence_scores.append(detection["confidence"])

                cropped_img = image.crop(bbox)

                if is_debug:
                    # Ensure the directory exists before saving
                    raw_debug_path = f"{self._debug_path}/raw_crop_{idx}.jpg"
                    os.makedirs(os.path.dirname(raw_debug_path), exist_ok=True)
                    cropped_img.save(raw_debug_path)
                    LOGGER.info(
                        f"📷 Saved raw cropped image: {raw_debug_path} (BBox: {bbox})"
                    )

                # Run OCR using OCRService
                raw_text = self.ocr_service.extract_text_from_image(cropped_img)
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

        return results
