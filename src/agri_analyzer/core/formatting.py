from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from time import perf_counter
from typing import Iterable

import pandas as pd


logger = logging.getLogger(__name__)


DATE_KEYWORDS = ("日期", "date", "time", "采样", "采收", "收获", "测定")
TREATMENT_KEYWORDS = ("处理", "分组", "group", "treatment", "control", "对照")
REPLICATE_KEYWORDS = ("小区", "重复", "rep", "replicate", "plot", "block", "区组")
INDEX_KEYWORDS = ("序号", "编号", "id", "index", "number", "no.")
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gbk", "gb18030")


class TableReadError(ValueError):
    pass


class ColumnDetectionError(ValueError):
    pass


@dataclass(frozen=True)
class ColumnDetection:
    date_column: str | None
    treatment_column: str | None
    replicate_column: str | None
    parameter_columns: list[str]
    needs_confirmation: bool
    messages: list[str]


def read_table(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    logger.debug("Reading table; path=%s; suffix=%s", file_path, suffix)
    try:
        if suffix == ".csv":
            df = _read_csv(file_path)
            logger.debug("CSV read complete; rows=%s; columns=%s", len(df), len(df.columns))
            return df
        if suffix in {".xlsx", ".xls"}:
            started_at = perf_counter()
            df = pd.read_excel(file_path)
            logger.debug(
                "Excel read complete in %.3fs; rows=%s; columns=%s",
                perf_counter() - started_at,
                len(df),
                len(df.columns),
            )
            return df
    except Exception as exc:
        logger.exception("Table read failed; path=%s", file_path)
        raise TableReadError(f"文件解析失败：{exc}") from exc
    raise TableReadError("仅支持 .xlsx、.xls 或 .csv 文件。")


def _read_csv(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in CSV_ENCODINGS:
        try:
            started_at = perf_counter()
            df = pd.read_csv(path, encoding=encoding)
            logger.debug(
                "CSV read complete in %.3fs with encoding=%s; rows=%s; columns=%s",
                perf_counter() - started_at,
                encoding,
                len(df),
                len(df.columns),
            )
            return df
        except UnicodeDecodeError as exc:
            last_error = exc
            logger.debug("CSV decode failed with encoding=%s; trying next.", encoding)
    if last_error:
        raise last_error
    return pd.read_csv(path)


def detect_columns(df: pd.DataFrame) -> ColumnDetection:
    logger.debug("Detecting columns; rows=%s; columns=%s", len(df), len(df.columns))
    if df.empty:
        raise ColumnDetectionError("表格为空，无法识别列。")

    columns = [str(column) for column in df.columns]
    date_column, date_confident = _detect_date_column(df, columns)
    treatment_column, treatment_confident = _detect_treatment_column(df, columns, date_column)
    replicate_column = _detect_replicate_column(df, columns, exclude={date_column, treatment_column})
    parameter_columns = _detect_numeric_columns(df, columns, exclude={date_column, treatment_column, replicate_column})

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
        replicate_column=replicate_column,
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
        if pd.to_numeric(df[column], errors="coerce").notna().mean() >= 0.8:
            continue
        parsed = _parse_date_series(df[column], allow_excel_serial=False)
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
        if any(keyword in column.lower() for keyword in INDEX_KEYWORDS):
            continue
        numeric = pd.to_numeric(df[column], errors="coerce")
        if numeric.notna().mean() >= 0.6:
            numeric_columns.append(column)
    return numeric_columns


def _detect_replicate_column(
    df: pd.DataFrame, columns: list[str], exclude: Iterable[str | None]
) -> str | None:
    excluded = {column for column in exclude if column}
    for column in columns:
        if column in excluded:
            continue
        if any(keyword in column.lower() for keyword in REPLICATE_KEYWORDS):
            return column
    return None


def format_parameters(
    df: pd.DataFrame,
    date_column: str,
    treatment_column: str,
    parameter_columns: list[str],
    replicate_column: str | None = None,
) -> pd.DataFrame:
    logger.debug(
        "Formatting parameters; rows=%s; date=%r; treatment=%r; parameters=%s",
        len(df),
        date_column,
        treatment_column,
        parameter_columns,
    )
    if not date_column or date_column not in df.columns:
        raise ColumnDetectionError("日期列不存在，请重新选择。")
    if not treatment_column or treatment_column not in df.columns:
        raise ColumnDetectionError("处理方式列不存在，请重新选择。")
    if not parameter_columns:
        raise ColumnDetectionError("请至少选择一个植株参数列。")

    missing = [column for column in parameter_columns if column not in df.columns]
    if missing:
        raise ColumnDetectionError(f"参数列不存在：{', '.join(missing)}")
    if replicate_column and replicate_column not in df.columns:
        raise ColumnDetectionError("小区/重复列不存在，请重新选择。")

    result = pd.DataFrame()
    started_at = perf_counter()
    parsed_dates = _parse_date_series(df[date_column], allow_excel_serial=True)
    logger.debug(
        "Date parsing complete in %.3fs; valid_dates=%s/%s",
        perf_counter() - started_at,
        int(parsed_dates.notna().sum()),
        len(parsed_dates),
    )
    if parsed_dates.isna().all():
        raise ColumnDetectionError("日期列无法解析为有效日期。")

    id_column = _detect_index_column(
        [str(column) for column in df.columns],
        exclude={date_column, treatment_column, replicate_column, *parameter_columns},
    )
    logger.debug("Index column detected: %r", id_column)
    result["序号"] = df[id_column] if id_column else range(1, len(df) + 1)
    result["日期"] = parsed_dates.dt.date
    result["isoweek"] = parsed_dates.dt.isocalendar().week.astype("Int64")
    result["处理方式"] = df[treatment_column].astype(str)
    if replicate_column:
        result["小区/重复"] = df[replicate_column].astype(str)
    for column in parameter_columns:
        logger.debug("Converting parameter column to numeric: %r", column)
        result[column] = pd.to_numeric(df[column], errors="coerce")
    logger.debug("Formatted dataframe ready; rows=%s; columns=%s", len(result), len(result.columns))
    return result


def _parse_date_series(series: pd.Series, allow_excel_serial: bool) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")
    numeric = pd.to_numeric(series, errors="coerce")
    numeric_ratio = float(numeric.notna().mean())
    if allow_excel_serial and numeric_ratio >= 0.8:
        valid = numeric.dropna()
        if not valid.empty and valid.between(20000, 80000).mean() >= 0.8:
            return pd.to_datetime(numeric, unit="D", origin="1899-12-30", errors="coerce")
    if numeric_ratio >= 0.8:
        return pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    return pd.to_datetime(series, errors="coerce")


def _detect_index_column(columns: list[str], exclude: Iterable[str | None]) -> str | None:
    excluded = {column for column in exclude if column}
    for column in columns:
        if column in excluded:
            continue
        if any(keyword in column.lower() for keyword in INDEX_KEYWORDS):
            return column
    return None
