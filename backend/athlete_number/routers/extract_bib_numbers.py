import asyncio
import os
from typing import List

import cv2
import numpy as np
import torch
from athlete_number.core.schemas import AthleteNumberResponse
from athlete_number.services.detection_orchestrator import DetectionOCRService
from athlete_number.utils.logger import setup_logger
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from athlete_number.gpu_config import parse_gpu_ids  # Import GPU parsing function

LOGGER = setup_logger(__name__)
router = APIRouter(prefix="/extract", tags=["Athlete Number Extraction"])

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 2))


async def get_orchestrator():
    """Initialize orchestrator with multi-GPU support."""
    yolo_gpus = parse_gpu_ids("YOLO_GPUS", [0])  # e.g., YOLO_GPUS="0,1"
    ocr_gpus = parse_gpu_ids("OCR_GPUS", [0])    # e.g., OCR_GPUS="2,3"
    return await DetectionOCRService.get_instance(yolo_gpus=yolo_gpus, ocr_gpus=ocr_gpus)


def load_image_from_upload(file: UploadFile) -> np.ndarray:
    """Load an image from an UploadFile object into a NumPy array."""
    image_bytes = file.file.read()
    image_np = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

    if image is None:
        LOGGER.error(f"❌ Failed to load image: {file.filename}")
        raise HTTPException(status_code=400, detail=f"Invalid or corrupted image: {file.filename}")

    return image


@router.post("/bib-numbers")
async def extract_athlete_numbers(
    files: List[UploadFile] = File(...),
    orchestrator: DetectionOCRService = Depends(get_orchestrator),  # Use orchestrator with multiple GPUs
) -> List[AthleteNumberResponse]:
    """API endpoint to process images using YOLO and OCR."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    LOGGER.info(f"Received {len(files)} images for processing (Batch Size: {BATCH_SIZE}).")

    images = [load_image_from_upload(file) for file in files]
    filenames = [file.filename for file in files]

    responses = []
    for i in range(0, len(filenames), BATCH_SIZE):
        batch_images = images[i : i + BATCH_SIZE]
        batch_filenames = filenames[i : i + BATCH_SIZE]

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        try:
            start_time = asyncio.get_event_loop().time()
            extracted_numbers_batch = await orchestrator.process_images(batch_images)
            processing_time = round(asyncio.get_event_loop().time() - start_time, 4)

            for filename, extracted_numbers in zip(batch_filenames, extracted_numbers_batch):
                responses.append(
                    AthleteNumberResponse(
                        filename=filename,
                        athlete_numbers=extracted_numbers if isinstance(extracted_numbers, list) else [extracted_numbers],
                    )
                )

        except torch.cuda.OutOfMemoryError:
            LOGGER.error("🔥 CUDA Out of Memory! Reduce batch size.")
            torch.cuda.empty_cache()
            raise HTTPException(status_code=500, detail="GPU out of memory. Try processing fewer images.")

    return responses

