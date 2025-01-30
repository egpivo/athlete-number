import asyncio
from typing import Dict, List

import numpy as np
import torch
from PIL import Image
from ultralytics import YOLO

from athlete_number.core.configs import YOLOv5_PATH
from athlete_number.services.utils import ModelPathResolver
from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)


class DigitDetector:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Load YOLO model once
        self.model = YOLO(model_path).to(self.device).eval()
        self._metadata = {"version": "1.0.0"}

    @property
    def model_version(self) -> str:
        return self._metadata.get("version", "1.0.0")

    @property
    def device_type(self) -> str:
        return "gpu" if torch.cuda.is_available() else "cpu"

    async def detect_async(self, image: Image.Image) -> List[Dict]:
        """Run detection asynchronously."""
        return await asyncio.to_thread(self.detect, image)

    def detect(self, image: Image.Image) -> List[Dict]:
        """Perform digit detection using YOLO model."""
        try:
            img_array = np.array(image)
            results = self.model.predict(
                img_array, conf=0.3, classes=list(range(10)), verbose=False
            )
            return self._format_results(results)
        except Exception as e:
            LOGGER.error(f"Inference failed: {e}")
            raise RuntimeError("Detection failed")

    def _format_results(self, results) -> List[Dict]:
        """Format YOLO results into a list of dictionaries."""
        detections = []
        for result in results:
            for box in result.boxes:
                xyxy = [
                    float(coord) for sublist in box.xyxy.tolist() for coord in sublist
                ]  # Flattened
                detections.append(
                    {
                        "digit": int(box.cls.item()),
                        "confidence": float(box.conf.item()),
                        "bbox": xyxy,
                    }
                )
        return sorted(detections, key=lambda x: x["bbox"][0])  # Sort by X-axis


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
                model_path = ModelPathResolver(YOLOv5_PATH).get_model_path()
                self.detector = DigitDetector(model_path)  # Load model here
                LOGGER.info("✅ Model initialized successfully.")
            except Exception as e:
                LOGGER.critical(f"❌ Model initialization failed: {e}")
                raise RuntimeError("Model initialization failed")
