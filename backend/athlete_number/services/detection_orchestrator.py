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
            # Initialize detection service
            self.detection_service = await DetectionService.get_instance(
                gpu_ids=self.yolo_gpus
            )

            # Initialize OCR services for each GPU
            for gpu_id in self.ocr_gpus:
                service = OCRService(gpu_id=gpu_id)
                self.ocr_services[gpu_id] = service
                LOGGER.info(f"Initialized OCR service on GPU {gpu_id}")

            LOGGER.info(f"YOLO GPUs: {self.yolo_gpus} | OCR GPUs: {self.ocr_gpus}")

    async def process_images(self, images: List[np.ndarray]) -> List[List[str]]:
        start_time = time.time()

        # Phase 1: Parallel detection
        detections = await self._parallel_detection(images)

        # Phase 2: Parallel OCR processing
        results = await self._parallel_ocr_processing(detections)

        LOGGER.info(f"Total processing time: {time.time() - start_time:.2f}s")
        return self._organize_results(results, detections)

    async def _parallel_detection(self, images: list):
        batches = split_list_evenly(images, len(self.yolo_gpus))

        tasks = [
            asyncio.create_task(self.detectors[gpu].detect(batch))
            for gpu, batch in zip(self.yolo_gpus, batches)
        ]

        results = await asyncio.gather(*tasks)
        detections = [detection for result in results for detection in result]

        return detections

    async def _parallel_ocr_processing(self, detections):
        """Distribute OCR across GPUs with load balancing"""
        all_crops = [
            Image.fromarray(det["image"])
            for detection in detections
            for det in detection
        ]

        # Split work evenly across OCR GPUs
        chunk_size = len(all_crops) // len(self.ocr_gpus) + 1
        futures = []
        for idx, gpu_id in enumerate(self.ocr_gpus):
            chunk = all_crops[idx * chunk_size : (idx + 1) * chunk_size]
            futures.append(
                self.executor.submit(
                    self.ocr_services[gpu_id].extract_numbers_from_images, chunk
                )
            )

        return await asyncio.gather(*[asyncio.wrap_future(f) for f in futures])

    def _organize_results(self, ocr_results, detections):
        """Reconstruct original image structure"""
        flat_results = [r for chunk in ocr_results for r in chunk]
        ptr = 0
        organized = []
        for detection in detections:
            num_crops = len(detection)
            organized.append(flat_results[ptr : ptr + num_crops])
            ptr += num_crops
        return organized
