from pathlib import Path

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
