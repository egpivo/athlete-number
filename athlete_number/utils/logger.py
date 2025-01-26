import logging
from typing import List, Optional


def setup_logger(
    name: Optional[str] = None,
    level: int = logging.DEBUG,
    filter_messages: Optional[List[str]] = None,
    log_to_file: bool = False,
    log_filename: str = "application.log",
) -> logging.Logger:
    class CustomFilter(logging.Filter):
        def __init__(self, messages: List[str]):
            self.messages = messages

        def filter(self, record):
            return not any(msg in record.getMessage() for msg in self.messages)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove all handlers associated with the logger
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    if not logger.hasHandlers():
        # StreamHandler for console logging
        ch = logging.StreamHandler()
        ch.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)

        if filter_messages:
            ch.addFilter(CustomFilter(filter_messages))

        logger.addHandler(ch)

        if log_to_file:
            fh = logging.FileHandler(log_filename)
            fh.setLevel(level)
            fh.setFormatter(formatter)

            if filter_messages:
                fh.addFilter(CustomFilter(filter_messages))

            logger.addHandler(fh)

    return logger
