"""
Centralised logging configuration for the application.
"""
import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a consistent format."""
    fmt = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Suppress noisy third-party loggers
    for lib in ("httpx", "openai", "urllib3", "matplotlib"):
        logging.getLogger(lib).setLevel(logging.WARNING)
