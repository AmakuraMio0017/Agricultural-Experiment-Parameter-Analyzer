from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
LOG_RETENTION_COUNT = 10
_ACTIVE_LOG_PATH: Path | None = None


def log_dir_path() -> Path:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
        return base_dir / "logs"
    return Path.cwd() / "outputs"


def log_file_path() -> Path:
    if _ACTIVE_LOG_PATH is not None:
        return _ACTIVE_LOG_PATH
    return log_dir_path() / "debug.log"


def configure_logging() -> Path:
    global _ACTIVE_LOG_PATH

    log_dir = log_dir_path()
    log_dir.mkdir(parents=True, exist_ok=True)
    if _ACTIVE_LOG_PATH is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _ACTIVE_LOG_PATH = log_dir / f"debug_{timestamp}.log"

    path = _ACTIVE_LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    existing_file_handlers = [
        handler
        for handler in root_logger.handlers
        if isinstance(handler, RotatingFileHandler)
        and Path(handler.baseFilename) == path
    ]
    if existing_file_handlers:
        return path

    file_handler = RotatingFileHandler(
        path,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(file_handler)

    _cleanup_old_logs(path.parent, active_path=path)
    logging.getLogger(__name__).info("Debug logging configured: %s", path)
    return path


def _cleanup_old_logs(
    log_dir: Path,
    keep_count: int | None = None,
    active_path: Path | None = None,
) -> None:
    keep_count = LOG_RETENTION_COUNT if keep_count is None else keep_count
    active_resolved = active_path.resolve() if active_path is not None else None
    logs = sorted(
        (
            item
            for item in log_dir.glob("debug_*.log*")
            if active_resolved is None or item.resolve() != active_resolved
        ),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    old_logs_to_keep = max(keep_count - (1 if active_path is not None else 0), 0)
    for old_log in logs[old_logs_to_keep:]:
        try:
            old_log.unlink()
        except OSError:
            logging.getLogger(__name__).warning("Failed to delete old log file: %s", old_log)
