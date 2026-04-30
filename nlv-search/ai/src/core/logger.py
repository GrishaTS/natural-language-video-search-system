import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    """Logging handler that forwards standard logging records to loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """Forward one standard logging record to loguru with preserved caller depth."""

        try:
            level = logger.level(record.levelname).name

        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2

        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logger(level: str = "INFO") -> None:
    """Configure loguru for the given log level."""

    log_level = level.upper()
    logger.remove()
    logger.add(
        sys.stdout,
        level=log_level,
        enqueue=True,
        backtrace=False,
        diagnose=False,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <5}</level> | "
            "<level>{message}</level>"
        ),
    )
    handler = InterceptHandler()
    logging.root.handlers = [handler]
    logging.root.setLevel(log_level)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        third_party_logger = logging.getLogger(name)
        third_party_logger.handlers = [handler]
        third_party_logger.propagate = False
        third_party_logger.setLevel(log_level)

    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
