import asyncio
import os
import time
from typing import List

from athlete_number.services.ocr import OCRService
from athlete_number.utils.logger import setup_logger
from PIL import Image

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
        """Runs YOLO detection and batch OCR pipeline for improved efficiency."""
        start_time = time.time()
        detections = await self.detection_service.detector.detect_async(image)

        if not detections:
            LOGGER.warning("⚠ No bib numbers detected.")
            return []

        # # Apply bbox validation and confidence filtering
        # filtered_detections = [
        #     d
        #     for d in detections
        #     if is_valid_bbox(d["bbox"]) and d["confidence"] >= MIN_CONFIDENCE
        # ]

        # if not filtered_detections:
        #     LOGGER.warning("⚠ All detections were filtered out.")
        #     return []

        self.last_detections = detections
        self.last_ocr_results = []

        # Extract detected regions as PIL images
        cropped_images = []
        for idx, detection in enumerate(detections):
            try:
                bbox = detection["bbox"]
                cropped_img = image.crop(bbox)
                cropped_images.append(cropped_img)

                if is_debug:
                    raw_debug_path = f"{self._debug_path}/raw_crop_{idx}.jpg"
                    os.makedirs(os.path.dirname(raw_debug_path), exist_ok=True)
                    cropped_img.save(raw_debug_path)
                    LOGGER.info(
                        f"📷 Saved raw cropped image: {raw_debug_path} (BBox: {bbox})"
                    )

            except Exception as e:
                LOGGER.error(f"❌ Failed to process detection: {e}", exc_info=True)

        ocr_results = self.ocr_service.extract_numbers_from_images(cropped_images)
        print(ocr_results)

        confidence_scores = [d["confidence"] for d in detections]
        self.last_confidence_score = (
            round(sum(confidence_scores) / len(confidence_scores), 4)
            if confidence_scores
            else 0.0
        )

        processing_time = round(time.time() - start_time, 4)

        LOGGER.info(
            f"🏅 Final Detected Athlete Numbers: {ocr_results} (Processing Time: {processing_time}s, Confidence: {self.last_confidence_score})"
        )

        return ocr_results
