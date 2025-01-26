from pathlib import Path

from athlete_number.utils.logger import setup_logger

LOGGER = setup_logger(__name__)


class ModelPathResolver:
    def __init__(self, model_path: str):
        self.model_path = Path(model_path)

    def get_model_path(self) -> str:
        if not self.model_path.exists():
            raise RuntimeError(
                f"❌ Model file {self.model_path} not found! Please download it manually."
            )
        return str(self.model_path)
