import asyncio
import os
import time
from typing import List

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
            LOGGER.info("✅ DetectionOCRService initialized.")

    async def process_images(
        self, images: List[Image.Image], is_debug: bool = False
    ) -> List[List[str]]:
        start_time = time.time()

        detections_batch = await self.detection_service.detector.detect_async(images)
        if not detections_batch:
            LOGGER.warning("⚠ No bib numbers detected in any image.")
            return [
                [] for _ in images
            ]  # Ensure result length matches input image count

        (
            cropped_images_per_image,
            confidence_scores_per_image,
        ) = await self.process_detections(images, detections_batch, is_debug)

        # Run OCR per image to maintain order
        ocr_results_per_image = [
            self.ocr_service.extract_numbers_from_images(cropped_images)
            for cropped_images in cropped_images_per_image
        ]

        flattened_confidence_scores = [
            score for sublist in confidence_scores_per_image for score in sublist
        ]

        avg_confidence = (
            round(
                sum(flattened_confidence_scores) / len(flattened_confidence_scores), 4
            )
            if flattened_confidence_scores
            else 0.0
        )

        self.last_confidence_scores.append(avg_confidence)

        processing_time = round(time.time() - start_time, 4)
        LOGGER.info(
            f"🏅 Final Detected Athlete Numbers: {ocr_results_per_image} "
            f"(Processing Time: {processing_time}s, Confidence: {avg_confidence})"
        )

        return ocr_results_per_image

    async def process_detections(
        self, images: List[Image.Image], detections_batch, is_debug: bool = False
    ):
        """Ensure cropped bib numbers remain correctly associated with each image."""
        cropped_images_per_image = []
        confidence_scores_per_image = []

        for img_idx, detections in enumerate(detections_batch or []):
            cropped_images = []
            confidence_scores = []

            # Ensure every image is accounted for, even if no detections
            if not detections:
                cropped_images_per_image.append([])
                confidence_scores_per_image.append([])
                continue  # Move to the next image

            for idx, detection in enumerate(detections):
                try:
                    bbox = detection.get("bbox")
                    confidence = detection.get("confidence", 0.0)

                    if bbox:
                        cropped_img = images[img_idx].crop(bbox)
                        resized_img = self.resize_image_with_width(
                            cropped_img, RESIZE_WIDTH
                        )
                        cropped_images.append(resized_img)
                        confidence_scores.append(confidence)

                        if is_debug:
                            debug_path = os.path.join(
                                self._debug_path, f"{img_idx}_crop_{idx}.jpg"
                            )
                            os.makedirs(os.path.dirname(debug_path), exist_ok=True)
                            resized_img.save(debug_path)

                except Exception as e:
                    LOGGER.error(
                        f"❌ Failed to process detection for image {img_idx}: {e}",
                        exc_info=True,
                    )

            cropped_images_per_image.append(cropped_images)
            confidence_scores_per_image.append(confidence_scores)

        return cropped_images_per_image, confidence_scores_per_image

    def resize_image_with_width(
        self, image: Image.Image, desired_width: int
    ) -> Image.Image:
        if image is None or image.size[0] == 0 or image.size[1] == 0:
            raise ValueError("Invalid image for processing.")

        # Calculate new height to maintain aspect ratio
        original_width, original_height = image.size
        scale_factor = desired_width / original_width
        new_height = int(original_height * scale_factor)

        return image.resize((desired_width, new_height), Image.LANCZOS)
