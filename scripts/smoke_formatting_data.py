from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agri_analyzer.core.formatting import (
    detect_columns,
    format_parameters,
    read_table,
)


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: python scripts/smoke_formatting_data.py <data-file>|--default-desktop",
            file=sys.stderr,
        )
        return 2

    if sys.argv[1] == "--default-desktop":
        path = Path.home() / "Desktop" / "20250524-单果重.xlsx"
        if not path.exists():
            print(f"Smoke data not found, skipped: {path}")
            return 0
    else:
        path = Path(sys.argv[1])

    if not path.exists():
        print(f"Smoke data file does not exist: {path}", file=sys.stderr)
        return 2

    df = read_table(path)
    detection = detect_columns(df)
    formatted = format_parameters(
        df,
        detection.date_column,
        detection.treatment_column,
        detection.parameter_columns,
    )

    if formatted.empty:
        print("Formatted dataframe is empty.", file=sys.stderr)
        return 1

    print(
        "Smoke data formatting passed:",
        path,
        f"source_rows={len(df)}",
        f"formatted_rows={len(formatted)}",
        f"columns={list(formatted.columns)}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
