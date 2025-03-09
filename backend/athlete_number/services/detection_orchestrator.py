import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

import numpy as np
from athlete_number.services.detection import DetectionService
from athlete_number.services.ocr import OCRService
from athlete_number.utils.logger import setup_logger
from PIL import Image

LOGGER = setup_logger(__name__)

def split_list_evenly(lst, n):
    """Split list into n evenly sized parts."""
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n)]


class DetectionOCRService:
    _instance = None

    def __init__(self, yolo_gpus=[0], ocr_gpus=[0]):
        self.yolo_gpus = yolo_gpus
        self.ocr_gpus = ocr_gpus
        self.detection_service = None
        self.ocr_services = {}
        self.executor = ThreadPoolExecutor(max_workers=len(ocr_gpus))
        self.lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls, yolo_gpus=[0], ocr_gpus=[0]):
        if cls._instance is None:
            cls._instance = cls(yolo_gpus, ocr_gpus)
            await cls._instance.initialize()
        return cls._instance

    async def initialize(self):
        async with self.lock:
            # Initialize YOLO Detection Service across multiple GPUs
            self.detection_service = await DetectionService.get_instance(
                gpu_ids=self.yolo_gpus
            )

            # Initialize multiple OCR services, one per GPU
            for gpu_id in self.ocr_gpus:
                service = OCRService(gpu_id=gpu_id)
                self.ocr_services[gpu_id] = service
                LOGGER.info(f"Initialized OCR service on GPU {gpu_id}")

            LOGGER.info(f"YOLO GPUs: {self.yolo_gpus} | OCR GPUs: {self.ocr_gpus}")

    async def process_images(self, images: List[np.ndarray]) -> List[List[str]]:
        start_time = time.time()

        # Step 1: Parallel Detection
        detections = await self._parallel_detection(images)

        # Step 2: Parallel OCR Processing
        results = await self._parallel_ocr_processing(detections)

        LOGGER.info(f"Total processing time: {time.time() - start_time:.2f}s")
        return self._organize_results(results, detections)

    async def _parallel_detection(self, images: list):
        """Distribute YOLO detection across multiple GPUs."""
        if not images:
            LOGGER.error("⚠️ No images provided for detection.")
            return []

        num_gpus = max(1, len(self.yolo_gpus))  # Avoid division by zero
        batches = split_list_evenly(images, num_gpus)

        # Ensure there is at least one batch
        batches = [batch for batch in batches if batch]  # Remove empty batches

        if not batches:
            LOGGER.error("⚠️ All batches are empty after splitting.")
            return []

        futures = [self.detection_service.detect_async(batch) for batch in batches]
        results = await asyncio.gather(*futures, return_exceptions=True)

        # Handle detection failures
        detections = []
        for result in results:
            if isinstance(result, Exception):
                LOGGER.error(f"❌ YOLO Detection failed: {result}")
            else:
                detections.extend(result)

        return detections

    async def _parallel_ocr_processing(self, detections):
        """Distribute OCR across GPUs with load balancing."""
        all_crops = [
            Image.fromarray(det["image"])
            for detection in detections
            for det in detection
        ]

        # Split work evenly across OCR GPUs
        chunk_size = max(1, len(all_crops) // len(self.ocr_gpus))  # Avoid zero-size chunks
        futures = []
        for idx, gpu_id in enumerate(self.ocr_gpus):
            chunk = all_crops[idx * chunk_size : (idx + 1) * chunk_size]
            if gpu_id in self.ocr_services:
                futures.append(
                    self.executor.submit(
                        self.ocr_services[gpu_id].extract_numbers_from_images, chunk
                    )
                )
            else:
                LOGGER.error(f"⚠️ OCR service for GPU {gpu_id} not initialized!")

        return await asyncio.gather(*[asyncio.wrap_future(f) for f in futures])

    def _organize_results(self, ocr_results, detections):
        """Reconstruct original image structure."""
        flat_results = [r for chunk in ocr_results for r in chunk]
        ptr = 0
        organized = []
        for detection in detections:
            num_crops = len(detection)
            organized.append(flat_results[ptr : ptr + num_crops])
            ptr += num_crops
        return organized

