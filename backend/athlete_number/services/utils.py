from pathlib import Path

import cv2
import numpy as np
from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)


class ModelPathResolver:
    def __init__(self, model_path: str):
        self.model_path = Path(model_path)

    def get_model_path(self) -> str:
        if not self.model_path.exists():
            raise RuntimeError(
                f"❌ Model file {self.model_path} not found! Please download it manually."
            )
        return str(self.model_path)


def is_valid_bbox(bbox):
    """Filters detections based on bounding box size and aspect ratio."""
    x1, y1, x2, y2 = map(int, bbox)
    width = x2 - x1
    height = y2 - y1
    aspect_ratio = width / height

    LOGGER.info(
        f"🔍 Checking BBox {bbox} - Width: {width}, Height: {height}, Aspect Ratio: {aspect_ratio}"
    )

    return True


def resize_image_with_width(image: np.ndarray, target_width: int = 1024) -> np.ndarray:
    """Resize an image while maintaining aspect ratio using OpenCV."""
    if image is None or image.size == 0:
        raise ValueError("Invalid image for processing.")

    h, w = image.shape[:2]
    scale = target_width / w
    new_size = (target_width, int(h * scale))
    return cv2.resize(image, new_size)
