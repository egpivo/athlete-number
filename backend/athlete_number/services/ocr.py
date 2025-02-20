import os
import re
from typing import List

import torch
from athlete_number.utils.logger import setup_logger
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

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

        self.model = AutoModelForImageTextToText.from_pretrained(self._model).to(
            self.device
        )
        self.processor = AutoProcessor.from_pretrained(self._model)

        # 🔥 Read batch size from environment variable, default = 4
        self.batch_size = int(os.getenv("OCR_BATCH_SIZE", 4))
        LOGGER.info(f"🔹 OCR batch size set to {self.batch_size}")

    @classmethod
    async def get_instance(cls):
        """Singleton pattern for OCR service."""
        if cls._instance is None:
            cls._instance = OCRService()
        return cls._instance

    def extract_numbers_from_images(self, images: List[Image.Image]) -> List[List[str]]:
        if not images:
            LOGGER.error("No images received for OCR processing.")
            return []

        try:
            all_results = []
            total_images = len(images)

            for i in range(0, total_images, self.batch_size):
                batch_images = images[i : i + self.batch_size]
                LOGGER.info(
                    f"📦 Processing batch {i // self.batch_size + 1}/{-(-total_images // self.batch_size)}"
                )
                inputs = self.processor(images=batch_images, return_tensors="pt").to(
                    self.device
                )

                with torch.no_grad():
                    generated_ids = self.model.generate(
                        **inputs,
                        do_sample=False,
                        tokenizer=self.processor.tokenizer,
                        stop_strings="<|im_end|>",
                        max_new_tokens=6,
                    )
                extracted_texts = self.processor.batch_decode(
                    generated_ids[:, inputs["input_ids"].shape[1] :],
                    skip_special_tokens=True,
                )
                cleaned_numbers = [
                    OCRService.extract_main_number(text) for text in extracted_texts
                ]
                all_results.extend(cleaned_numbers)

                # 🔥 Cleanup GPU memory after each batch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()

            LOGGER.info(f"🔍 GOT-OCR-2.0 Final Output: {all_results}")
            return all_results
        except Exception as e:
            LOGGER.exception(f"❌ GOT-OCR-2.0 batch processing failed - {e}.")
            return [[] for _ in images]

    @staticmethod
    def extract_main_number(text: str) -> str:
        digit_groups = re.findall(r"\d+", text)
        return max(digit_groups, key=len) if digit_groups else ""
