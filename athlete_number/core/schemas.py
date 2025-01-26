from pydantic import BaseModel


class TextExtractionResponse(BaseModel):
    extracted_text: str
