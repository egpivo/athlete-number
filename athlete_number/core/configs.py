import os

from dotenv import load_dotenv

load_dotenv()

YOLOv5_PATH = os.getenv("YOLOv5_PATH", "models/best.pt")  # Default fallback
