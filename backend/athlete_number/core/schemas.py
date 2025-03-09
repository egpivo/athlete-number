from typing import List

from pydantic import BaseModel


class NumberExtractionResponse(BaseModel):
    filename: str
    extracted_number: List[str]


class AthleteNumberResponse(BaseModel):
    filename: str
    athlete_numbers: List[str]
