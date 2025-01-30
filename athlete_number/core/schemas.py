from typing import Dict, List

from pydantic import BaseModel


class NumberExtractionResponse(BaseModel):
    filename: str
    extracted_number: List[str]


class DetectionResult(BaseModel):
    class_id: int
    confidence: float
    bbox: list[float]


class DetectionResponse(BaseModel):
    filename: str
    detections: list[DetectionResult]
    metadata: dict


class AthleteNumberResponse(BaseModel):
    filename: str
    athlete_numbers: List[str]
    yolo_detections: List[Dict]
    ocr_results: List[str]
    processing_time: float
    confidence: float
    model_versions: Dict[str, str]
