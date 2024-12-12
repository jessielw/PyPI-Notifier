import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def init_logger(log_directory: Path) -> logging.Logger:
    logger = logging.getLogger("pypi_notifiar")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = RotatingFileHandler(
        str(log_directory / "pypi_notifiar.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
