from typing import List

from pydantic import BaseModel


class NumberExtractionResponse(BaseModel):
    extracted_number: str


class DetectionResult(BaseModel):
    digit: int
    confidence: float
    bbox: list[float]


class DetectionResponse(BaseModel):
    detections: list[DetectionResult]
    metadata: dict


class AthleteNumberResponse(BaseModel):
    athlete_number: str
    yolo_detections: list
    ocr_results: List[str]  # OCR outputs
    processing_time: float
    confidence: float  # Combined confidence score
    model_versions: dict
