import asyncio
import concurrent.futures
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

        self.last_ocr_results = []
        self.last_confidence_scores = []

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

    async def process_images(
        self, images: List[Image.Image], is_debug: bool = False
    ) -> List[List[str]]:
        start_time = time.time()

        detections_batch = await self.detection_service.detector.detect_async(
            images
        )  # Assuming it supports batch
        if not detections_batch:
            LOGGER.warning("⚠ No bib numbers detected in any image.")
            return []

        cropped_images, confidence_scores = await self.process_detections(
            images, detections_batch, is_debug
        )
        ocr_results = self.ocr_service.extract_numbers_from_images(cropped_images)

        avg_confidence = (
            round(sum(confidence_scores) / len(confidence_scores), 4)
            if confidence_scores
            else 0.0
        )
        self.last_confidence_scores.append(avg_confidence)

        processing_time = round(time.time() - start_time, 4)
        LOGGER.info(
            f"🏅 Final Detected Athlete Numbers: {ocr_results} "
            f"(Processing Time: {processing_time}s, Confidence: {avg_confidence})"
        )

        return ocr_results

    async def process_detections(
        self, images: List[Image.Image], detections_batch, is_debug: bool = False
    ):
        """Optimized function to process multiple detections in parallel."""
        cropped_images = []
        confidence_scores = []

        def crop_and_save(image, detection, idx):
            """Helper function to crop images and optionally save debug images."""
            try:
                bbox = detection.get("bbox")
                confidence = detection.get("confidence", 0.0)

                if bbox and confidence >= MIN_CONFIDENCE:
                    cropped_img = image.crop(bbox)
                    confidence_scores.append(confidence)

                    if is_debug:
                        raw_debug_path = os.path.join(
                            self._debug_path, f"raw_crop_{idx}.jpg"
                        )
                        os.makedirs(os.path.dirname(raw_debug_path), exist_ok=True)
                        cropped_img.save(raw_debug_path)

                    return cropped_img
            except Exception as e:
                LOGGER.error(f"❌ Failed to process detection: {e}", exc_info=True)
            return None

        # 🔥 Use ThreadPoolExecutor for **parallel** cropping
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(crop_and_save, images[img_idx], detection, idx)
                for img_idx, detections in enumerate(detections_batch)
                for idx, detection in enumerate(detections)
            ]
            cropped_images = [
                f.result()
                for f in concurrent.futures.as_completed(futures)
                if f.result()
            ]

        return cropped_images, confidence_scores
