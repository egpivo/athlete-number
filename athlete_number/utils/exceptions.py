from fastapi import HTTPException

from athlete_number.utils.logger import logger


def handle_errors_and_logging(exception: Exception, status_code: int, detail: str):
    error_message = f"{detail}: {str(exception)}"
    logger.exception(error_message)
    raise HTTPException(status_code=status_code, detail=error_message)
