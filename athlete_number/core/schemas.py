from typing import Dict, List

from pydantic import BaseModel


class NumberExtractionResponse(BaseModel):
    extracted_number: List[str]


class DetectionResult(BaseModel):
    class_id: int
    confidence: float
    bbox: list[float]


class DetectionResponse(BaseModel):
    detections: list[DetectionResult]
    metadata: dict


class AthleteNumberResponse(BaseModel):
    athlete_numbers: List[str]
    yolo_detections: List[Dict]
    ocr_results: List[str]
    processing_time: float
    confidence: float
    model_versions: Dict[str, str]
