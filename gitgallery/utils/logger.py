"""
Central logging for GitGallery.

Logs uploads, deletions, repository operations, sync events, and errors
to logs/gitgallery.log and optionally to console.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Lazy-initialized logger; setup_logging() must be called at app start
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Return the application logger. Raises if logging not yet configured."""
    global _logger
    if _logger is None:
        raise RuntimeError("Logging not initialized. Call setup_logging() first.")
    return _logger


def setup_logging(
    log_dir: Path,
    log_filename: str = "gitgallery.log",
    level: int = logging.INFO,
    console: bool = True,
) -> logging.Logger:
    """
    Configure and return the application logger.

    Args:
        log_dir: Directory for log file.
        log_filename: Name of the log file.
        level: Logging level.
        console: Whether to also log to stderr.

    Returns:
        The configured Logger instance.
    """
    global _logger
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / log_filename

    _logger = logging.getLogger("gitgallery")
    _logger.setLevel(level)
    _logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    _logger.addHandler(fh)

    if console:
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(level)
        ch.setFormatter(fmt)
        _logger.addHandler(ch)

    return _logger
