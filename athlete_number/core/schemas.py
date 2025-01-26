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
