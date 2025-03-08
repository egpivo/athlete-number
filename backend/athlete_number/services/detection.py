import asyncio
from typing import Dict, List

import numpy as np
import torch
from athlete_number.core.configs import YOLO_PATH
from athlete_number.services.utils import ModelPathResolver, resize_image_with_width
from athlete_number.utils.logger import setup_logger
from torch import nn
from ultralytics import YOLO

LOGGER = setup_logger(__name__)


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
            self.model = YOLO(model_path).to(self.device)

            # Add compatibility wrapper
            if not hasattr(self.model.model[0], "bn"):
                for m in self.model.model.modules():
                    if isinstance(m, nn.Conv2d):
                        m.bn = nn.BatchNorm2d(m.out_channels)
                        m.act = nn.SiLU()

        self._metadata = {"version": "1.0.0"}

    @property
    def model_version(self) -> str:
        return self._metadata.get("version", "1.0.0")

    @property
    def device_type(self) -> str:
        return "gpu" if torch.cuda.is_available() else "cpu"

    async def detect_async(self, images: List[np.ndarray]) -> List[List[Dict]]:
        """Run detection asynchronously."""
        return await asyncio.to_thread(self.detect, images)

    def detect(self, images: List[np.ndarray]) -> List[List[Dict]]:
        try:
            results = self.model(
                images,
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
            LOGGER.error(f"Inference failed: {e}")
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

    def __init__(self, gpu_ids=[0, 1]):
        self.detectors = []
        self.lock = asyncio.Lock()
        self.gpu_ids = gpu_ids

    @classmethod
    async def get_instance(cls, gpu_ids=[0, 1]):
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
        try:
            # Split images across available detectors
            chunks = np.array_split(images, len(self.detectors))

            # Create parallel detection tasks
            futures = [
                detector.detect_async(chunk)
                for detector, chunk in zip(self.detectors, chunks)
            ]

            # Gather and combine results
            results = await asyncio.gather(*futures)
            return [item for sublist in results for item in sublist]

        except Exception as e:
            LOGGER.error(f"Parallel detection failed: {e}")
            return []
