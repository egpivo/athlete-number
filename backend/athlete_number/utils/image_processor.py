from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image


class ImageHandler:
    @staticmethod
    async def validate_and_convert(file: UploadFile) -> Image.Image:
        """Convert upload file to PIL Image with validation"""
        if not file.content_type.startswith("image/"):
            raise HTTPException(400, "Invalid file type")

        try:
            content = await file.read()
            return Image.open(BytesIO(content)).convert("RGB")
        except Exception as e:
            raise HTTPException(400, f"Image processing failed: {str(e)}")
