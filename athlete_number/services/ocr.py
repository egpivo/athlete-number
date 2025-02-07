import re
from typing import List

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)


class OCRService:
    _instance = None
    _model = "stepfun-ai/GOT-OCR-2.0-hf"

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        if OCRService._instance is not None:
            raise RuntimeError(
                "OCRService is a singleton class. Use get_instance() instead."
            )

        # Load OCR Model & Processor
        self.model = AutoModelForImageTextToText.from_pretrained(self._model).to(
            self.device
        )
        self.processor = AutoProcessor.from_pretrained(self._model)

    @classmethod
    async def get_instance(cls):
        """Singleton pattern for OCR service."""
        if cls._instance is None:
            cls._instance = OCRService()
        return cls._instance

    def preprocess_image(
        self,
        image: Image.Image,
        apply_auto_invert: bool = False,
        auto_invert_threshold: float = 110.0,
    ) -> np.ndarray:
        if isinstance(image, Image.Image):
            image = np.array(image)

        if image is None or image.size == 0:
            raise ValueError("Invalid image for OCR processing.")

        if len(image.shape) == 3:
            processed = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            processed = image.copy()

        h, w = processed.shape[:2]
        if w != 0 and w != 500:
            new_width = 500
            scale_factor = new_width / w
            new_height = int(h * scale_factor)
            processed = cv2.resize(processed, (new_width, new_height))

        if apply_auto_invert:
            mean_val = np.mean(processed)
            if mean_val > auto_invert_threshold:
                processed = cv2.bitwise_not(processed)

        processed_rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
        return processed_rgb

    def extract_numbers_from_images(self, images: List[Image.Image]) -> List[List[str]]:
        try:
            processed_images = [
                Image.fromarray(self.preprocess_image(np.array(img))) for img in images
            ]
            inputs = self.processor(images=processed_images, return_tensors="pt").to(
                self.device
            )

            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    do_sample=False,
                    tokenizer=self.processor.tokenizer,
                    stop_strings="<|im_end|>",
                    max_new_tokens=4096,
                )
            extracted_texts = self.processor.batch_decode(
                generated_ids[:, inputs["input_ids"].shape[1] :],
                skip_special_tokens=True,
            )
            cleaned_numbers = [self.clean_ocr_output(text) for text in extracted_texts]

            LOGGER.info(f"🔍 GOT-OCR-2.0 Batch Output: {cleaned_numbers}")
            return cleaned_numbers
        except Exception as e:
            LOGGER.exception(f"❌ GOT-OCR-2.0 batch processing failed - {e}.")
            return [[] for _ in images]

    def clean_ocr_output(self, text: str) -> str:
        text = text.replace(" ", "")
        cleaned_text = re.sub(r"[^0-9a-zA-Z]", "", text)
        return cleaned_text if cleaned_text else "N/A"
