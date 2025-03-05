import asyncio
from typing import Dict, List

import cv2
import numpy as np
import torch
from athlete_number.core.configs import YOLO_PATH
from athlete_number.services.utils import ModelPathResolver
from athlete_number.utils.logger import setup_logger
from ultralytics import YOLO

LOGGER = setup_logger(__name__)


def resize_image_with_width(image: np.ndarray, target_width: int) -> np.ndarray:
    """Resize an image while maintaining aspect ratio using OpenCV."""
    if image is None or image.size == 0:
        raise ValueError("Invalid image for processing.")

    h, w = image.shape[:2]
    scale = target_width / w
    new_size = (target_width, int(h * scale))
    return cv2.resize(image, new_size)


class DigitDetector:
    def __init__(
        self,
        model_path: str,
        conf: float = 0.5,
        iou: float = 0.5,
        max_det: int = 100,
        image_size: int = 1280,
    ):
        self.model_path = model_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.conf = conf
        self.iou = iou
        self.max_det = max_det
        self.image_size = image_size

        self.model = YOLO(model_path).to(self.device)
        self._metadata = {"version": "1.0.0"}

    @property
    def model_version(self) -> str:
        return self._metadata.get("version", "1.0.0")

    @property
    def device_type(self) -> str:
        return "gpu" if torch.cuda.is_available() else "cpu"

    async def detect_async(self, image_files: List[str]) -> List[List[Dict]]:
        """Run detection asynchronously."""
        return await asyncio.to_thread(self.detect, image_files)

    def detect(self, image_files: List[str]) -> List[List[Dict]]:
        try:
            results = self.model(
                image_files,
                imgsz=self.image_size,
                conf=self.conf,
                iou=self.iou,
                max_det=self.max_det,
                augment=True,
            )
            return [
                self._format_results(result, image_files[idx])
                for idx, result in enumerate(results)
            ]
        except Exception as e:
            LOGGER.error(f"Inference failed: {e}")
            raise RuntimeError("Detection failed")

    def _format_results(self, result, filename: str) -> List[Dict]:
        detections = []
        orig_img = (
            result.orig_img if hasattr(result, "orig_img") else cv2.imread(filename)
        )

        dets = result.boxes
        boxes_conf = list(zip(dets.xyxy.tolist(), dets.conf.tolist()))
        boxes_conf.sort(key=lambda x: x[1], reverse=True)

        for bbox_xyxy, conf_score in boxes_conf:
            x1, y1, x2, y2 = map(int, bbox_xyxy)
            cropped_img = orig_img[y1:y2, x1:x2]

            # Resize cropped image
            processed_rgb = resize_image_with_width(cropped_img, 1024)

            # Store the detection info
            detections.append(
                {
                    "filename": filename,
                    "bbox": bbox_xyxy,
                    "confidence": float(conf_score),
                    "image": processed_rgb,
                }
            )

        return detections


class DetectionService:
    _instance = None

    def __init__(self):
        self.detector = None
        self.lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            cls._instance = DetectionService()
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
                LOGGER.info("✅ Model initialized successfully.")
            except Exception as e:
                LOGGER.critical(f"❌ Model initialization failed: {e}")
                raise RuntimeError("Model initialization failed")
