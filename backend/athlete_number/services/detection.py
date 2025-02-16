import asyncio
from typing import Dict, List

import torch
from athlete_number.core.configs import YOLO_PATH
from athlete_number.services.utils import ModelPathResolver
from athlete_number.utils.logger import setup_logger
from PIL import Image
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

    async def detect_async(self, image: List[Image.Image]) -> List[List[Dict]]:
        """Run detection asynchronously."""
        return await asyncio.to_thread(self.detect, image)

    def detect(self, images: List[Image.Image]) -> List[List[Dict]]:
        try:
            results = self.model(
                images,
                imgsz=self.image_size,
                conf=self.conf,
                iou=self.iou,
                max_det=self.max_det,
                augment=True,
            )
            return [self._format_results(result) for result in results]
        except Exception as e:
            LOGGER.error(f"Inference failed: {e}")
            raise RuntimeError("Detection failed")

    def _format_results(self, results) -> List[Dict]:
        detections = []
        for result in results:
            for box in result.boxes:
                xyxy = [
                    float(coord) for sublist in box.xyxy.tolist() for coord in sublist
                ]
                detections.append(
                    {
                        "class_id": int(box.cls.item()),
                        "confidence": float(box.conf.item()),
                        "bbox": xyxy,
                    }
                )
        return sorted(detections, key=lambda x: x["bbox"][0])


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
