import asyncio
from typing import Dict, List

import torch
from PIL import Image
from yolov5 import YOLOv5

from athlete_number.services.model_loader import ModelLoader
from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)


class DigitDetector:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = YOLOv5(model_path, device=self.device)
        self._metadata = {"version": "1.0.0"}  # Example metadata

    @property
    def model_version(self) -> str:
        return self._metadata.get("version", "1.0.0")

    @property
    def device_type(self) -> str:
        return "gpu" if torch.cuda.is_available() else "cpu"

    def is_ready(self) -> bool:
        return self.model is not None

    async def detect_async(self, image: Image.Image) -> List[Dict]:
        """Run detection asynchronously."""
        return await asyncio.to_thread(self.detect, image)

    def detect(self, image: Image.Image) -> List[Dict]:
        """Perform digit detection using YOLOv5."""
        # Convert PIL Image to numpy array
        img_array = np.array(image)

        # Run inference
        results = self.model.predict(
            img_array, conf=0.5, classes=list(range(10)), verbose=False
        )

        return self._format_results(results)

    def _format_results(self, results) -> List[Dict]:
        """Format YOLOv5 results into a list of dictionaries."""
        detections = []
        for *xyxy, conf, cls in results.xyxy[0]:
            detections.append(
                {
                    "digit": int(cls),
                    "confidence": float(conf),
                    "bbox": [float(coord) for coord in xyxy],
                }
            )
        # Sort detections by x-coordinate
        return sorted(detections, key=lambda x: x["bbox"][0])


class DetectionService:
    """Singleton class to manage model lifecycle."""

    _instance = None

    def __init__(self):
        self.detector = None
        self.lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls, model_url: str):
        if cls._instance is None:
            cls._instance = DetectionService()
            await cls._instance.initialize(model_url)
        return cls._instance

    async def initialize(self, model_url: str):
        """Asynchronously initialize the DigitDetector."""
        async with self.lock:
            if self.detector is not None:
                return
            try:
                model_loader = ModelLoader(model_url)
                model_path = await asyncio.to_thread(model_loader.download_model)
                self.detector = DigitDetector(model_path)
                LOGGER.info("Model initialized successfully.")
            except Exception as e:
                LOGGER.critical(f"Model initialization failed: {e}")
                raise RuntimeError("Model initialization failed")
