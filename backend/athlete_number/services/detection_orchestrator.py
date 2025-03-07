import asyncio
import time
from typing import List

import numpy as np
from athlete_number.services.ocr import OCRService
from athlete_number.utils.logger import setup_logger
from PIL import Image

LOGGER = setup_logger(__name__)

RESIZE_WIDTH = 1024


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
            LOGGER.info("DetectionOCRService initialized.")

    async def process_images(self, images: List[np.ndarray]) -> List[List[str]]:
        start_time = time.time()

        detections_batch = await self.detection_service.detector.detect_async(images)
        if not detections_batch:
            LOGGER.warning("⚠ No bib numbers detected in any image.")
            return [[] for _ in images]
        pil_images = [
            [Image.fromarray(det["image"]) for det in detection]
            for detection in detections_batch
        ]
        ocr_results_per_image = []
        for image_list in pil_images:
            ocr_results_per_image.append(
                self.ocr_service.extract_numbers_from_images(image_list)
            )

        processing_time = round(time.time() - start_time, 4)
        LOGGER.info(
            f"Final Detected Athlete Numbers: {ocr_results_per_image} "
            f"(Processing Time: {processing_time}s"
        )

        return ocr_results_per_image
