import asyncio
import os

import numpy as np
import torch
import uvicorn
from athlete_number.routers.detect_bib_numbers import router as detect_router
from athlete_number.routers.extract_bib_numbers import router as athlete_router
from athlete_number.routers.extract_numbers import router as extract_router
from athlete_number.services.detection import DetectionService
from athlete_number.utils.logger import setup_logger
from dotenv import load_dotenv
from fastapi import FastAPI
from PIL import Image

load_dotenv()
app = FastAPI()

MODEL_LOADED = False  # Prevent multiple model initializations
LOGGER = setup_logger(__name__)


@app.get("/")
async def read_main():
    return {"message": "Welcome!"}


app.include_router(extract_router)
app.include_router(detect_router)
app.include_router(athlete_router)


@app.on_event("startup")
async def load_model():
    """Preload the model only once in the main worker."""
    global MODEL_LOADED
    if MODEL_LOADED:
        print("🚀 Model already loaded. Skipping reload.")
        return

    LOGGER.info("🔄 Preloading model to avoid cold start...")
    detection_service = await DetectionService.get_instance()
    detector = detection_service.detector

    dummy_image = Image.fromarray(np.zeros((1, 1, 3), dtype=np.uint8))

    # Ensure the model is correctly loaded on GPU
    with torch.no_grad():
        await asyncio.to_thread(detector.detect, [dummy_image])

    MODEL_LOADED = True  # Mark model as loaded
    torch.cuda.empty_cache()  # Free any unused memory
    LOGGER.info("✅ Model preloaded successfully.")


def main():
    """Start the FastAPI app with Uvicorn."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5566))
    reload = os.getenv("RELOAD", "TRUE").lower() == "true"

    uvicorn.run("athlete_number.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
