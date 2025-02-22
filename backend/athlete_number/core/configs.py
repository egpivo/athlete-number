import os

from athlete_number.utils.logger import setup_logger

logger = setup_logger(__name__)

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
YOLO_PATH = os.path.join(BACKEND_DIR, "models/best.pt")

logger.info(f"✅ Using dynamically resolved YOLO model path: {YOLO_PATH}")

# Ensure the model file actually exists
if not os.path.exists(YOLO_PATH):
    raise RuntimeError(f"❌ Model file not found at: {YOLO_PATH}")
