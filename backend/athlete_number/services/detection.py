import asyncio
from typing import Dict, List

import numpy as np
import torch
from athlete_number.core.configs import YOLO_PATH
from athlete_number.services.utils import ModelPathResolver, resize_image_with_width
from athlete_number.utils.logger import setup_logger
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
        gpu_ids=[0, 1],
    ):
        self.model_path = model_path
        self.device = f"cuda:{gpu_ids[0]}" if torch.cuda.is_available() else "cpu"
        self.gpu_ids = gpu_ids  # Store assigned GPUs

        self.conf = conf
        self.iou = iou
        self.max_det = max_det
        self.image_size = image_size

        self.model = YOLO(model_path).to(self.device)
        if torch.cuda.device_count() > 1:
            LOGGER.info(f"🔹 Using GPUs {gpu_ids} for YOLO inference")
            self.model = torch.nn.DataParallel(self.model, device_ids=gpu_ids)

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
            model_instance = getattr(self.model, "module", self.model)
            results = model_instance(
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
        self.detector = None
        self.lock = asyncio.Lock()
        self.gpu_ids = gpu_ids

    @classmethod
    async def get_instance(cls, gpu_ids=[0, 1]):
        if cls._instance is None:
            cls._instance = DetectionService(gpu_ids=gpu_ids)
            await cls._instance.initialize()
        return cls._instance

    async def initialize(self):
        """Asynchronously initialize the DigitDetector."""
        async with self.lock:
            if self.detector is not None:
                return
            try:
                model_path = ModelPathResolver(YOLO_PATH).get_model_path()
                self.detector = DigitDetector(model_path)
                LOGGER.info("Model initialized successfully.")
            except Exception as e:
                LOGGER.critical(f"Model initialization failed: {e}")
                raise RuntimeError("Model initialization failed")
