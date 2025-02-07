import re
from typing import List

import numpy as np
import torch
from transformers import AutoModelForImageTextToText, AutoProcessor

from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)


def clean_ocr_output(text: str) -> str:
    """Cleans OCR output to remove misclassified characters."""
    text = text.replace(" ", "")
    text = re.sub(r"[^0-9a-zA-Z]", "", text)
    return text


def parse_numbers(texts: List[str]) -> List[str]:
    return [num for text in texts for num in re.findall(r"[0-9a-zA-Z]+", text)]


device = "cuda" if torch.cuda.is_available() else "cpu"


class OCRService:
    _instance = None

    def __init__(self):
        if OCRService._instance is not None:
            raise RuntimeError(
                "OCRService is a singleton class. Use get_instance() instead."
            )

        # Load OCR model and processor
        self.model = AutoModelForImageTextToText.from_pretrained(
            "stepfun-ai/GOT-OCR-2.0-hf"
        ).to(device)
        self.processor = AutoProcessor.from_pretrained("stepfun-ai/GOT-OCR-2.0-hf")

    @classmethod
    async def get_instance(cls):
        """Singleton pattern for OCR service."""
        if cls._instance is None:
            cls._instance = OCRService()
        return cls._instance

    def clean_ocr_output(self, text: str) -> str:
        """Cleans OCR output to remove misclassified characters."""
        text = text.replace(" ", "")
        return re.sub(r"[^0-9a-zA-Z]", "", text)

    def parse_numbers(self, texts: List[str]) -> List[str]:
        """Extracts alphanumeric characters from OCR results."""
        return [num for text in texts for num in re.findall(r"[0-9a-zA-Z]+", text)]

    def extract_text_from_image(self, image: np.ndarray) -> str:
        """Extracts text using GOT-OCR-2.0 instead of Tesseract."""
        try:
            # Convert numpy image to PIL Image
            pil_image = Image.fromarray(image)

            # Preprocess image
            inputs = self.processor(images=pil_image, return_tensors="pt").to(device)

            # Run inference
            with torch.no_grad():
                generated_ids = self.model.generate(**inputs)

            # Decode output
            extracted_text = self.processor.batch_decode(
                generated_ids, skip_special_tokens=True
            )[0]
            results = self.parse_numbers([extracted_text])

            LOGGER.info(f"🔍 GOT-OCR-2.0 Output: {results}")
            return "".join(results)
        except Exception as e:
            LOGGER.exception(f"❌ GOT-OCR-2.0 failed to extract text - {e}.")
            return ""

    def clean_numbers(self, text: str) -> str:
        """Extracts numbers and letters from text."""
        numbers = re.findall(r"[0-9a-zA-Z]+", text)
        return "".join(numbers) if numbers else ""
