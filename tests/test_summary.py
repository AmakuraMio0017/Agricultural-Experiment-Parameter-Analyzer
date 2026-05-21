import math
from pathlib import Path

import pandas as pd

from src.agri_analyzer.core.formatting import detect_columns, format_parameters, read_table
from src.agri_analyzer.core.summary import (
    detect_parameter_columns,
    plot_treatment_summary,
    summarize_by_treatment,
)


def formatted_sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "序号": [1, 2, 3, 4, 5],
            "日期": pd.to_datetime(
                ["2026-04-01", "2026-04-01", "2026-04-01", "2026-04-01", "2026-04-01"]
            ).date,
            "isoweek": [14, 14, 14, 14, 14],
            "处理方式": ["对照", "对照", "处理", "处理", "单样本"],
            "单果重": [10, 14, 15, 17, 20],
            "备注": ["a", "b", "c", "d", "e"],
        }
    )


def test_detect_parameter_columns_uses_numeric_non_fixed_columns() -> None:
    assert detect_parameter_columns(formatted_sample()) == ["单果重"]


def test_summarize_by_treatment_calculates_descriptive_statistics() -> None:
    summary = summarize_by_treatment(formatted_sample(), "单果重")
    control = summary.loc[summary["处理方式"] == "对照"].iloc[0]
    treated = summary.loc[summary["处理方式"] == "处理"].iloc[0]

    assert control["n"] == 2
    assert control["mean"] == 12
    assert round(control["sd"], 4) == round(math.sqrt(8), 4)
    assert control["sem"] == 2
    assert treated["mean"] == 16
    assert treated["diff_vs_control"] == 4
    assert round(treated["diff_percent_vs_control"], 4) == 33.3333


def test_summarize_by_treatment_leaves_control_diff_empty_without_control() -> None:
    df = formatted_sample().replace({"对照": "基准"})
    summary = summarize_by_treatment(df, "单果重")

    assert summary["diff_vs_control"].isna().all()
    assert summary["diff_percent_vs_control"].isna().all()


def test_summarize_by_treatment_keeps_single_sample_error_as_nan() -> None:
    summary = summarize_by_treatment(formatted_sample(), "单果重")
    single = summary.loc[summary["处理方式"] == "单样本"].iloc[0]

    assert single["n"] == 1
    assert pd.isna(single["sd"])
    assert pd.isna(single["sem"])


def test_plot_treatment_summary_writes_file(tmp_path: Path) -> None:
    summary = summarize_by_treatment(formatted_sample(), "单果重")
    output = tmp_path / "summary.png"

    figure = plot_treatment_summary(summary, "单果重", output_path=output)

    assert output.exists()
    assert output.stat().st_size > 0
    figure.clear()


def test_example_data_source_can_flow_through_module_two() -> None:
    path = Path("example_data_sources/TestDataSource.xlsx")
    if not path.exists():
        return

    source = read_table(path)
    detection = detect_columns(source)
    formatted = format_parameters(
        source,
        detection.date_column,
        detection.treatment_column,
        detection.parameter_columns,
    )
    assert "单果重" in detect_parameter_columns(formatted)

    summary = summarize_by_treatment(formatted, "单果重")

    assert set(summary["处理方式"]) == {"处理", "对照"}
    assert summary.loc[summary["处理方式"] == "对照", "n"].iloc[0] == 78
    assert summary.loc[summary["处理方式"] == "处理", "n"].iloc[0] == 75
