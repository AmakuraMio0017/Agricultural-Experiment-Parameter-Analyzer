from pathlib import Path

import pandas as pd

from src.agri_analyzer.core.formatting import detect_columns, format_parameters, read_table


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "日期": ["2026-04-01", "2026-04-08"],
            "处理方式": ["对照", "处理A"],
            "单果重": [18.2, 21.0],
            "糖度": [9.5, 10.6],
            "备注": ["样本1", "样本2"],
        }
    )


def test_read_csv_returns_dataframe(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    sample_frame().to_csv(path, index=False, encoding="utf-8-sig")

    df = read_table(path)

    assert not df.empty
    assert "日期" in df.columns


def test_read_excel_returns_dataframe(tmp_path: Path) -> None:
    path = tmp_path / "sample.xlsx"
    sample_frame().to_excel(path, index=False)

    df = read_table(path)

    assert not df.empty
    assert "处理方式" in df.columns


def test_detect_columns_identifies_date_treatment_and_numeric_parameters() -> None:
    detection = detect_columns(sample_frame())

    assert detection.date_column == "日期"
    assert detection.treatment_column == "处理方式"
    assert detection.parameter_columns == ["单果重", "糖度"]


def test_format_parameters_adds_isoweek_and_fixed_headers() -> None:
    formatted = format_parameters(sample_frame(), "日期", "处理方式", ["单果重"])

    assert list(formatted.columns) == ["序号", "日期", "isoweek", "处理方式", "单果重"]
    assert formatted.loc[0, "序号"] == 1
    assert formatted.loc[0, "isoweek"] == 14


def test_format_parameters_removes_unselected_parameters() -> None:
    formatted = format_parameters(sample_frame(), "日期", "处理方式", ["糖度"])

    assert "糖度" in formatted.columns
    assert "单果重" not in formatted.columns


def test_excel_serial_date_column_is_detected_and_formatted() -> None:
    df = pd.DataFrame(
        {
            "数据序号": [1, 2],
            "采收日": [46106, 46106],
            "处理情况": ["处理", "对照"],
            "单果重": [12.78, 13.2],
        }
    )

    detection = detect_columns(df)
    formatted = format_parameters(
        df,
        detection.date_column,
        detection.treatment_column,
        detection.parameter_columns,
    )

    assert detection.date_column == "采收日"
    assert detection.treatment_column == "处理情况"
    assert detection.parameter_columns == ["单果重"]
    assert str(formatted.loc[0, "日期"]) == "2026-03-25"
    assert formatted.loc[0, "isoweek"] == 13


def test_format_parameters_preserves_source_id_column_when_available() -> None:
    df = pd.DataFrame(
        {
            "数据序号": [101, 205],
            "采收日": [46106, 46106],
            "处理情况": ["处理", "对照"],
            "单果重": [12.78, 13.2],
        }
    )

    formatted = format_parameters(df, "采收日", "处理情况", ["单果重"])

    assert formatted["序号"].tolist() == [101, 205]
