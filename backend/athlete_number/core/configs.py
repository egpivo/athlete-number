import os

from dotenv import load_dotenv

load_dotenv()

YOLO_PATH = os.getenv("YOLO_PATH", "models/best.pt")
