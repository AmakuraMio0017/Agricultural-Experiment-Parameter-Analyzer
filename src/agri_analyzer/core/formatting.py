from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


DATE_KEYWORDS = ("日期", "date", "time", "采样", "测定")
TREATMENT_KEYWORDS = ("处理", "分组", "group", "treatment", "control", "对照")
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gbk", "gb18030")


class TableReadError(ValueError):
    pass


class ColumnDetectionError(ValueError):
    pass


@dataclass(frozen=True)
class ColumnDetection:
    date_column: str | None
    treatment_column: str | None
    parameter_columns: list[str]
    needs_confirmation: bool
    messages: list[str]


def read_table(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".csv":
            return _read_csv(file_path)
        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(file_path)
    except Exception as exc:
        raise TableReadError(f"文件解析失败：{exc}") from exc
    raise TableReadError("仅支持 .xlsx、.xls 或 .csv 文件。")


def _read_csv(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in CSV_ENCODINGS:
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    return pd.read_csv(path)


def detect_columns(df: pd.DataFrame) -> ColumnDetection:
    if df.empty:
        raise ColumnDetectionError("表格为空，无法识别列。")

    columns = [str(column) for column in df.columns]
    date_column, date_confident = _detect_date_column(df, columns)
    treatment_column, treatment_confident = _detect_treatment_column(df, columns, date_column)
    parameter_columns = _detect_numeric_columns(df, columns, exclude={date_column, treatment_column})

    messages: list[str] = []
    if not date_column:
        messages.append("未能识别日期列。")
    elif not date_confident:
        messages.append(f"日期列候选为“{date_column}”，建议确认。")

    if not treatment_column:
        messages.append("未能识别处理方式列。")
    elif not treatment_confident:
        messages.append(f"处理方式列候选为“{treatment_column}”，建议确认。")

    if not parameter_columns:
        messages.append("未能识别可计算的植株参数列。")

    return ColumnDetection(
        date_column=date_column,
        treatment_column=treatment_column,
        parameter_columns=parameter_columns,
        needs_confirmation=bool(messages) or len(parameter_columns) > 1,
        messages=messages,
    )


def _detect_date_column(df: pd.DataFrame, columns: list[str]) -> tuple[str | None, bool]:
    for column in columns:
        if any(keyword in column.lower() for keyword in DATE_KEYWORDS):
            return column, True

    scores: list[tuple[str, float]] = []
    for column in columns:
        parsed = pd.to_datetime(df[column], errors="coerce")
        score = float(parsed.notna().mean())
        if score >= 0.6:
            scores.append((column, score))
    if not scores:
        return None, False
    scores.sort(key=lambda item: item[1], reverse=True)
    return scores[0][0], len(scores) == 1 and scores[0][1] >= 0.85


def _detect_treatment_column(
    df: pd.DataFrame, columns: list[str], date_column: str | None
) -> tuple[str | None, bool]:
    for column in columns:
        if column == date_column:
            continue
        if any(keyword in column.lower() for keyword in TREATMENT_KEYWORDS):
            return column, True

    candidates: list[tuple[str, int]] = []
    row_count = max(len(df), 1)
    for column in columns:
        if column == date_column:
            continue
        series = df[column]
        numeric_ratio = pd.to_numeric(series, errors="coerce").notna().mean()
        unique_count = series.dropna().astype(str).nunique()
        if numeric_ratio < 0.5 and 2 <= unique_count <= max(20, row_count // 2):
            candidates.append((column, unique_count))
    if not candidates:
        return None, False
    candidates.sort(key=lambda item: item[1])
    return candidates[0][0], len(candidates) == 1


def _detect_numeric_columns(
    df: pd.DataFrame, columns: list[str], exclude: Iterable[str | None]
) -> list[str]:
    excluded = {column for column in exclude if column}
    numeric_columns: list[str] = []
    for column in columns:
        if column in excluded:
            continue
        numeric = pd.to_numeric(df[column], errors="coerce")
        if numeric.notna().mean() >= 0.6:
            numeric_columns.append(column)
    return numeric_columns


def format_parameters(
    df: pd.DataFrame,
    date_column: str,
    treatment_column: str,
    parameter_columns: list[str],
) -> pd.DataFrame:
    if not date_column or date_column not in df.columns:
        raise ColumnDetectionError("日期列不存在，请重新选择。")
    if not treatment_column or treatment_column not in df.columns:
        raise ColumnDetectionError("处理方式列不存在，请重新选择。")
    if not parameter_columns:
        raise ColumnDetectionError("请至少选择一个植株参数列。")

    missing = [column for column in parameter_columns if column not in df.columns]
    if missing:
        raise ColumnDetectionError(f"参数列不存在：{', '.join(missing)}")

    result = pd.DataFrame()
    parsed_dates = pd.to_datetime(df[date_column], errors="coerce")
    if parsed_dates.isna().all():
        raise ColumnDetectionError("日期列无法解析为有效日期。")

    result["序号"] = range(1, len(df) + 1)
    result["日期"] = parsed_dates.dt.date
    result["isoweek"] = parsed_dates.dt.isocalendar().week.astype("Int64")
    result["处理方式"] = df[treatment_column].astype(str)
    for column in parameter_columns:
        result[column] = pd.to_numeric(df[column], errors="coerce")
    return result
