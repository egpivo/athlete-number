import os

import numpy as np
import torch
import uvicorn
from athlete_number.routers.extract_bib_numbers import router as athlete_router
from athlete_number.services.detection import DetectionService
from athlete_number.utils.logger import setup_logger
from fastapi import FastAPI

app = FastAPI()
LOGGER = setup_logger(__name__)

MODEL_LOADED = False


@app.get("/")
async def root():
    return {"message": "Welcome!"}


app.include_router(athlete_router)


@app.get("/warmup")
async def warmup():
    """Trigger model loading to prevent cold starts."""
    LOGGER.info("🚀 Running warm-up inference...")

    detection_service = await DetectionService.get_instance()
    await detection_service.run_warmup()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    LOGGER.info("✅ Warm-up complete!")
    return {"status": "Warm-up successful"}


@app.on_event("startup")
async def load_model():
    """Preload the model at startup."""
    global MODEL_LOADED
    if not MODEL_LOADED:
        LOGGER.info("🔄 Loading model at startup...")
        detection_service = await DetectionService.get_instance()
        dummy_image = np.zeros((640, 640, 3), dtype=np.uint8)

        await detection_service.detect_async([dummy_image])

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        MODEL_LOADED = True
        LOGGER.info("✅ Model loaded at startup!")


@app.get("/health")
async def health_check():
    return {"status": "Healthy"}


@app.get("/")
async def root():
    return {"message": "Welcome to the Athlete Number Detection API!"}


async def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5566))
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
