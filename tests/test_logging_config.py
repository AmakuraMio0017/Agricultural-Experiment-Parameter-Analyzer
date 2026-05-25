import logging
import sys
from pathlib import Path

from src.agri_analyzer.utils import logging_config


def test_configure_logging_creates_timestamped_log_and_retains_recent_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(logging_config, "_ACTIVE_LOG_PATH", None)
    monkeypatch.setattr(logging_config, "LOG_RETENTION_COUNT", 3)

    for index in range(5):
        old_log = tmp_path / "outputs" / f"debug_20260101_00000{index}.log"
        old_log.parent.mkdir(parents=True, exist_ok=True)
        old_log.write_text("old", encoding="utf-8")

    path = logging_config.configure_logging()

    assert path.parent == tmp_path / "outputs"
    assert path.name.startswith("debug_")
    assert path.name.endswith(".log")
    assert path.name != "debug.log"
    assert logging_config.log_file_path() == path
    assert len(list(path.parent.glob("debug_*.log*"))) <= 3

    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if getattr(handler, "baseFilename", None) == str(path):
            root_logger.removeHandler(handler)
            handler.close()
