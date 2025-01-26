import os
from pathlib import Path

import aiofiles
import httpx
import torch

from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)


class ModelLoader:
    """Download and validate PyTorch models with async support"""

    def __init__(
        self,
        model_url: str,
        model_dir: str = "models",
        force_redownload: bool = False,
    ):
        self.model_url = model_url
        self.model_dir = Path(model_dir)
        self.model_path = self.model_dir / Path(model_url).name
        self.force_redownload = force_redownload

    async def download_model_async(self) -> str:
        """Async version of model download workflow"""
        try:
            self.model_dir.mkdir(exist_ok=True)
            if self._should_download():
                await self._download_async()
            self._validate()
            return str(self.model_path)
        except Exception as e:
            LOGGER.error(f"Async model management failed: {e}")
            raise

    async def _download_async(self) -> None:
        """Async implementation of model download"""
        temp_path = self.model_path.with_suffix(".tmp")
        try:
            if self.model_path.exists():
                self.model_path.unlink()

            LOGGER.info(f"Starting async download from {self.model_url}")
            async with httpx.AsyncClient() as client:
                response = await client.get(self.model_url)
                response.raise_for_status()

                async with aiofiles.open(temp_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        await f.write(chunk)

            temp_path.rename(self.model_path)
            LOGGER.info("Async model download completed")
        except Exception as e:
            if temp_path.exists():
                os.remove(temp_path)
            raise RuntimeError(f"Async download failed: {e}")

    def download_model(self):
        """Smart model download with validation and version control"""
        try:
            self.model_dir.mkdir(exist_ok=True)

            if self._should_download():
                self._download()

            self._validate()
            return str(self.model_path)

        except Exception as e:
            LOGGER.error(f"Model management failed: {str(e)}")
            raise

    def _should_download(self) -> bool:
        """Determine if download is needed"""
        if self.force_redownload:
            LOGGER.info("Forcing model redownload")
            return True

        if not self.model_path.exists():
            LOGGER.info("Model not found locally")
            return True

        return False

    def _download(self) -> None:
        """Download model with atomic write."""
        temp_path = self.model_path.with_suffix(".tmp")
        try:
            if self.model_path.exists():
                self.model_path.unlink()

            LOGGER.info(f"Downloading model from {self.model_url}")
            with httpx.stream("GET", self.model_url, follow_redirects=True) as response:
                response.raise_for_status()
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)

            temp_path.rename(self.model_path)
            LOGGER.info("Model downloaded successfully.")
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Download failed: {e}")

    def _validate(self):
        """Run comprehensive validation checks"""
        # 1. File existence check
        if not self.model_path.exists():
            raise FileNotFoundError("Model file missing after download")
        try:
            torch.load(self.model_path, map_location="cpu")
            LOGGER.info("Model validation passed")
        except Exception as e:
            self.model_path.unlink()
            raise RuntimeError(f"Model loading failed: {str(e)}")
