import os
import re
from typing import List

import torch
from athlete_number.utils.logger import setup_logger
from dotenv import load_dotenv
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

load_dotenv()

LOGGER = setup_logger(__name__)

BIB_NUM_LENGTH = int(os.getenv("BIB_NUM_LENGTH", "0"))


class OCRService:
    _instance = None
    _model = "stepfun-ai/GOT-OCR-2.0-hf"

    def __init__(self, gpu_ids=[2, 3]):  # Assign OCR to GPUs 2 & 3
        self.device = f"cuda:{gpu_ids[0]}" if torch.cuda.is_available() else "cpu"
        self.gpu_ids = gpu_ids

        if OCRService._instance is not None:
            raise RuntimeError(
                "OCRService is a singleton class. Use get_instance() instead."
            )

        self.model = AutoModelForImageTextToText.from_pretrained(self._model).to(
            self.device
        )
        if torch.cuda.device_count() > 1:
            LOGGER.info(f"🔹 Using GPUs {gpu_ids} for OCR inference")
            self.model = torch.nn.DataParallel(self.model, device_ids=gpu_ids)

        self.processor = AutoProcessor.from_pretrained(self._model)

        # Read batch size from environment variable, default = 4
        self.batch_size = int(os.getenv("OCR_BATCH_SIZE", 8))
        LOGGER.info(f"🔹 OCR batch size set to {self.batch_size}")

    @classmethod
    async def get_instance(cls, gpu_ids=[2, 3]):  # Assign GPUs dynamically
        if cls._instance is None:
            cls._instance = OCRService(gpu_ids=gpu_ids)
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
                model_instance = getattr(self.model, "module", self.model)
                with torch.no_grad():
                    generated_ids = model_instance.generate(
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
                filtered_numbers = [num for num in cleaned_numbers if num]
                all_results.extend(filtered_numbers)

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()

            LOGGER.info(f"🔍 GOT-OCR-2.0 Final Output: {all_results}")
            return all_results
        except Exception as e:
            LOGGER.exception(f"❌ GOT-OCR-2.0 batch processing failed - {e}.")
            return [[] for _ in images]

    @staticmethod
    def extract_main_number(text: str, num_length: int = BIB_NUM_LENGTH) -> str:
        digit_groups = re.findall(r"\d+", text)
        filtered_numbers = [
            num for num in digit_groups if num_length and len(num) == num_length
        ]
        return max(filtered_numbers, key=len) if filtered_numbers else ""
