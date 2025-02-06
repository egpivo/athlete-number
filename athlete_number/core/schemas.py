from typing import List

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
