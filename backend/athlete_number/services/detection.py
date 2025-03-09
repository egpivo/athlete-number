import asyncio
from typing import Dict, List

import numpy as np
import torch
from athlete_number.core.configs import YOLO_PATH
from athlete_number.services.utils import ModelPathResolver, resize_image_with_width
from athlete_number.utils.logger import setup_logger
from ultralytics import YOLO
from PIL import Image

LOGGER = setup_logger(__name__)
import math

def split_evenly(images, gpu_count):
    """Split images into gpu_count non-empty chunks (where possible)."""
    if gpu_count <= 0:
        return []

    # If images < gpu_count, some GPUs will indeed get empty lists.
    # Minimally ensure we don't create more slices than images:
    gpu_count = min(gpu_count, len(images))

    chunk_size = math.ceil(len(images) / gpu_count)
    return [images[i*chunk_size : (i+1)*chunk_size] for i in range(gpu_count)]



class DigitDetector:
    def __init__(
        self,
        model_path: str,
        conf: float = 0.5,
        iou: float = 0.5,
        max_det: int = 100,
        image_size: int = 1280,
        gpu_id=0,
    ):
        self.model_path = model_path
        self.device = f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu"
        self.conf = conf
        self.iou = iou
        self.max_det = max_det
        self.image_size = image_size

        # Load model on specific GPU
        with torch.cuda.device(gpu_id):
            self.model = YOLO(model_path, task="detect").to(self.device)
            LOGGER.info(f"Loaded YOLO on {self.device} with GPU ID {gpu_id}")

        self._metadata = {"version": "1.0.0"}

    @property
    def model_version(self) -> str:
        return self._metadata.get("version", "1.0.0")

    @property
    def device_type(self) -> str:
        return "gpu" if torch.cuda.is_available() else "cpu"

    async def detect_async(self, images: List[np.ndarray]) -> List[List[Dict]]:
        """Ensure images are properly formatted before detection."""
    
        if images is None or len(images) == 0:
            LOGGER.error("❌ detect_async() received an empty list!")
            return []

        if isinstance(images, np.ndarray):  # If a single NumPy array is mistakenly passed
            LOGGER.warning("⚠️ detect_async() received a single NumPy array instead of a list. Converting to list.")
            images = [images]  # Convert it into a list

        if not isinstance(images, list):
            LOGGER.error(f"❌ detect_async() expected a list but got {type(images)}")
            return []

        return await asyncio.to_thread(self.detect, images)


    def detect(self, images: List[np.ndarray]) -> List[List[Dict]]:
        try:
            if images is None or len(images) == 0:
                LOGGER.error("❌ detect() received an empty list!")
                raise ValueError("No images provided for detection.")

            if not isinstance(images, list):
                LOGGER.error(f"❌ detect() expected a list but got {type(images)}")
                return []

            # 🚨 Ensure all images are valid NumPy arrays
            for i, img in enumerate(images):
                if img is None or not isinstance(img, np.ndarray):
                    LOGGER.error(f"❌ Image {i} is invalid! Type: {type(img)}")
                    raise ValueError(f"Invalid image at index {i}. Expected np.ndarray but got {type(img)}")

                if img.size == 0:
                    LOGGER.error(f"❌ Image {i} is empty! Shape: {img.shape}")
                    raise ValueError(f"Empty image at index {i}.")

            # ✅ Convert NumPy arrays to PIL images
            pil_images = [Image.fromarray(image) for image in images]

            LOGGER.info(f"✅ Running YOLO on {len(pil_images)} images. Image size: {self.image_size}")

            results = self.model(
                pil_images,
                imgsz=self.image_size,
                conf=self.conf,
                iou=self.iou,
                max_det=self.max_det,
                augment=True,
            )

            return [
                self._format_results(result, images[idx])
                for idx, result in enumerate(results)
            ]

        except Exception as e:
            LOGGER.error(f"❌ Inference failed: {e}")
            raise RuntimeError("Detection failed")


    def _format_results(self, result, orig_img) -> List[Dict]:
        detections = []
        dets = result.boxes
        boxes_conf = list(zip(dets.xyxy.tolist(), dets.conf.tolist()))
        boxes_conf.sort(key=lambda x: x[1], reverse=True)

        for bbox_xyxy, conf_score in boxes_conf:
            x1, y1, x2, y2 = map(int, bbox_xyxy)
            cropped_img = orig_img[y1:y2, x1:x2]

            processed_rgb = resize_image_with_width(cropped_img)
            detections.append(
                {
                    "bbox": bbox_xyxy,
                    "confidence": float(conf_score),
                    "image": processed_rgb,
                }
            )

        return detections

class DetectionService:
    _instance = None

    def __init__(self, gpu_ids=[0]):
        self.detectors = []
        self.lock = asyncio.Lock()
        self.gpu_ids = gpu_ids

    @classmethod
    async def get_instance(cls, gpu_ids=[0]):
        """Singleton pattern with multi-GPU support"""
        if cls._instance is None:
            cls._instance = DetectionService(gpu_ids=gpu_ids)
            await cls._instance.initialize()
        return cls._instance

    async def initialize(self):
        """Initialize multiple YOLO detectors on different GPUs"""
        async with self.lock:
            if self.detectors:
                return

            try:
                model_path = ModelPathResolver(YOLO_PATH).get_model_path()
                self.detectors = [
                    DigitDetector(model_path, gpu_id=gpu_id) for gpu_id in self.gpu_ids
                ]
                LOGGER.info(f"🔥 Initialized YOLO detectors on GPUs {self.gpu_ids}")
            except Exception as e:
                LOGGER.critical(f"Model initialization failed: {e}")
                raise RuntimeError("Detection service startup failed")

    async def detect_async(self, images: List[np.ndarray]) -> List[List[Dict]]:
        """Parallel detection across multiple GPUs"""
        if not isinstance(images, list):
            LOGGER.warning("⚠️ detect_async() received a single NumPy array instead of a list. Converting...")
            images = [images]

        LOGGER.info(f"✅ Received {len(images)} images for detection. Shapes: {[img.shape for img in images]}")

        # Ensure no empty images are sent
        images = [img for img in images if img is not None and img.size > 0]

        if not images:
            LOGGER.error("❌  detect_async() received an empty list!")
            return []

        # 🔥 Call detect() on each YOLO detector
        #return await asyncio.to_thread(self._run_parallel_detection, images)
        return await self._run_parallel_detection(images)

    async def _run_parallel_detection(self, images):
        """Distribute images across multiple YOLO detectors"""
        num_gpus = len(self.detectors)
        #batches = [images[i::num_gpus] for i in range(num_gpus)]  # Distribute images
        batches = split_evenly(images, num_gpus)
        futures = []
        for detector, batch in zip(self.detectors, batches):
            if not batch:
                LOGGER.info("⚠️ This GPU got an empty batch. Skipping.")
                continue
            # Launch detection in a thread, pinned to the detector's GPU
            futures.append(asyncio.to_thread(detector.detect, batch))

        # Wait for all GPUs to finish in parallel
        results = await asyncio.gather(*futures)

        # Flatten results
        combined = []
        for r in results:
            combined.extend(r)
        return combined

        #results = []
        #for idx, (detector, batch) in enumerate(zip(self.detectors, batches)):
        #    if not batch:
        #        LOGGER.info(f"⚠️ GPU {idx} has an empty batch. Skipping detect().")
        #        continue
        
            # Each 'detector' can do something like 'detector.detect(batch)'
        #    detection = detector.detect(batch)
        #    results.extend(detection)

        #return results
