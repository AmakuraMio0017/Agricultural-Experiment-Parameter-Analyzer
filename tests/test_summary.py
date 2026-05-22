import math
from pathlib import Path

import pandas as pd

from src.agri_analyzer.core.formatting import detect_columns, format_parameters, read_table
from src.agri_analyzer.core.summary import (
    detect_outliers,
    detect_parameter_columns,
    format_outliers_for_output,
    format_summary_for_output,
    plot_treatment_summary,
    round_significant,
    summarize_by_treatment,
    summarize_with_outliers,
)


def formatted_sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "序号": [101, 102, 201, 202, 203, 204, 301],
            "日期": pd.to_datetime(
                [
                    "2026-04-01",
                    "2026-04-01",
                    "2026-04-01",
                    "2026-04-01",
                    "2026-04-01",
                    "2026-04-01",
                    "2026-04-01",
                ]
            ).date,
            "isoweek": [14, 14, 14, 14, 14, 14, 14],
            "处理方式": ["对照", "对照", "处理", "处理", "处理", "处理", "单样本"],
            "单果重": [10, 14, 15, 17, 18, 100, 20],
            "备注": ["a", "b", "c", "d", "e", "outlier", "g"],
        }
    )


def test_detect_parameter_columns_uses_numeric_non_fixed_columns() -> None:
    assert detect_parameter_columns(formatted_sample()) == ["单果重"]


def test_round_significant_keeps_three_significant_digits_and_integer_ids() -> None:
    assert round_significant(11.5823) == 11.6
    assert round_significant(0.179123) == 0.179
    assert round_significant(151) == 151
    assert pd.isna(round_significant(float("nan")))


def test_summarize_by_treatment_calculates_descriptive_statistics_without_outlier() -> None:
    summary = summarize_by_treatment(formatted_sample(), "单果重")
    control = summary.loc[summary["处理方式"] == "对照"].iloc[0]
    treated = summary.loc[summary["处理方式"] == "处理"].iloc[0]

    assert control["n"] == 2
    assert control["mean"] == 12
    assert round(control["sd"], 4) == round(math.sqrt(8), 4)
    assert control["sem"] == 2
    assert treated["n"] == 3
    assert round(treated["mean"], 4) == 16.6667
    assert round(treated["diff_vs_control"], 4) == 4.6667
    assert round(treated["diff_percent_vs_control"], 4) == 38.8889


def test_detect_outliers_reports_group_iqr_outlier_with_source_id() -> None:
    outliers = detect_outliers(formatted_sample(), "单果重")

    assert len(outliers) == 1
    row = outliers.iloc[0]
    assert row["参数"] == "单果重"
    assert row["序号"] == 204
    assert row["处理方式"] == "处理"
    assert row["原始值"] == 100
    assert row["判定规则"] == "组内 IQR 1.5倍"


def test_summarize_with_outliers_returns_clean_summary_and_report() -> None:
    summary, outliers = summarize_with_outliers(formatted_sample(), "单果重")

    assert len(outliers) == 1
    assert summary.loc[summary["处理方式"] == "处理", "n"].iloc[0] == 3


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


def test_output_formatters_round_summary_and_keep_empty_outlier_columns() -> None:
    summary, outliers = summarize_with_outliers(formatted_sample(), "单果重")
    formatted_summary = format_summary_for_output(summary)
    formatted_outliers = format_outliers_for_output(outliers.iloc[0:0])

    assert formatted_summary.loc[formatted_summary["处理方式"] == "处理", "mean"].iloc[0] == 16.7
    assert formatted_summary.loc[formatted_summary["处理方式"] == "处理", "n"].iloc[0] == 3
    assert list(formatted_outliers.columns) == [
        "参数",
        "序号",
        "日期",
        "isoweek",
        "处理方式",
        "原始值",
        "下限",
        "上限",
        "判定规则",
    ]
    assert formatted_outliers.empty


def test_plot_treatment_summary_writes_file_and_uses_narrow_bars_and_padded_ylim(tmp_path: Path) -> None:
    summary = summarize_by_treatment(formatted_sample(), "单果重")
    output = tmp_path / "summary.png"

    figure = plot_treatment_summary(summary, "单果重", output_path=output)
    ax = figure.axes[0]

    assert output.exists()
    assert output.stat().st_size > 0
    assert round(ax.patches[0].get_width(), 2) == 0.4
    centers = [patch.get_x() + patch.get_width() / 2 for patch in ax.patches]
    assert centers == [1.0, 2.0, 3.0]
    assert ax.get_xlim() == (0.0, 4.0)
    ymin, ymax = ax.get_ylim()
    error = summary["sem"].fillna(0)
    expected_min = float((summary["mean"] - error).min())
    expected_max = float((summary["mean"] + error).max())
    assert ymin < expected_min
    assert ymax > expected_max
    assert ymin > 0
    figure.clear()


def test_two_group_plot_uses_equal_axis_spacing_and_error_labels(tmp_path: Path) -> None:
    summary = summarize_by_treatment(formatted_sample(), "单果重").iloc[:2].reset_index(drop=True)
    output = tmp_path / "two_group_summary.png"

    figure = plot_treatment_summary(summary, "单果重", output_path=output)
    ax = figure.axes[0]

    centers = [patch.get_x() + patch.get_width() / 2 for patch in ax.patches]
    labels = [text.get_text() for text in ax.texts]
    highest_label_y = max(text.get_position()[1] for text in ax.texts)

    assert output.exists()
    assert centers == [1.0, 2.0]
    assert ax.get_xlim() == (0.0, 3.0)
    assert round(ax.patches[0].get_width(), 2) == 0.4
    assert labels == ["12 ± 2", "16.7 ± 0.882"]
    assert ax.get_ylim()[1] > highest_label_y
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

    summary, outliers = summarize_with_outliers(formatted, "单果重")

    assert set(summary["处理方式"]) == {"处理", "对照"}
    assert "序号" in outliers.columns
