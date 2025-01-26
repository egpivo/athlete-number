from pydantic import BaseModel


class TextExtractionResponse(BaseModel):
    extracted_text: str


class DetectionResult(BaseModel):
    digit: int
    confidence: float
    bbox: list[float]


class DetectionResponse(BaseModel):
    detections: list[DetectionResult]
    metadata: dict
