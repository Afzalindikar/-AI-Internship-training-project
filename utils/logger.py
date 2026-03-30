"""
utils/logger.py
---------------
Structured logging for the extraction pipeline.
Supports console (colorlog) and file (output/pipeline.log) handlers.
"""

import logging
import os
from pathlib import Path

try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False

_LOGGERS: dict = {}


def get_logger(name: str = "pipeline", level: str = "INFO",
               log_dir: str = "output") -> logging.Logger:
    """
    Get or create a named logger with console + file handlers.

    Args:
        name    : Logger name (default: "pipeline")
        level   : Logging level string — INFO | DEBUG | ERROR | WARNING
        log_dir : Directory for the log file

    Returns:
        Configured logging.Logger instance
    """
    global _LOGGERS
    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(name)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    if logger.handlers:
        logger.handlers.clear()

    fmt = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    # ── Console handler ──────────────────────────────────────────────────────
    import sys as _sys
    # Ensure stdout is UTF-8 safe on Windows
    _stream = _sys.stdout
    try:
        if hasattr(_stream, "reconfigure"):
            if not (_stream.encoding or "").lower().startswith("utf"):
                _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if HAS_COLORLOG:
        color_fmt = (
            "%(log_color)s[%(asctime)s] [%(levelname)s]%(reset)s "
            "[%(name)s] %(message)s"
        )
        console_handler = colorlog.StreamHandler(stream=_stream)
        console_handler.setFormatter(colorlog.ColoredFormatter(
            color_fmt,
            datefmt=date_fmt,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            }
        ))
    else:
        console_handler = logging.StreamHandler(stream=_stream)
        console_handler.setFormatter(logging.Formatter(fmt, datefmt=date_fmt))

    console_handler.setLevel(numeric_level)
    logger.addHandler(console_handler)

    # ── File handler ─────────────────────────────────────────────────────────
    try:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_path = os.path.join(log_dir, "pipeline.log")
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(fmt, datefmt=date_fmt))
        file_handler.setLevel(numeric_level)
        logger.addHandler(file_handler)
    except Exception as exc:  # pragma: no cover
        logger.warning(f"Could not create file log handler: {exc}")

    logger.propagate = False
    _LOGGERS[name] = logger
    return logger


def step_log(logger: logging.Logger, step: str, message: str,
             job_id: str = "", level: str = "info") -> None:
    """
    Emit a clearly labelled pipeline-step log line.

    Args:
        logger  : Logger instance
        step    : Pipeline step name, e.g. DETECT | EXTRACT | CLEAN
        message : Human-readable message
        job_id  : Optional job identifier
        level   : Log level (info/debug/error/warning)
    """
    prefix = f"[{step.upper()}]"
    if job_id:
        prefix = f"[{step.upper()}][{job_id[:8]}]"
    full_msg = f"{prefix} {message}"
    getattr(logger, level.lower(), logger.info)(full_msg)
