from pathlib import Path

import pandas as pd

from src.agri_analyzer.core.formatting import detect_columns, format_parameters, read_table
from src.agri_analyzer.core.significance import (
    analyze_significance,
    plot_significance_summary,
    p_value_to_stars,
    tukey_letter_groups,
)
from src.agri_analyzer.core.summary import OUTLIER_NOTE, detect_parameter_columns


def two_group_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "序号": range(1, 9),
            "日期": pd.to_datetime(["2026-04-01"] * 8).date,
            "isoweek": [14] * 8,
            "处理方式": ["对照"] * 4 + ["处理"] * 4,
            "单果重": [10, 11, 12, 13, 20, 21, 22, 23],
        }
    )


def multi_group_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "序号": range(1, 16),
            "日期": pd.to_datetime(["2026-04-01"] * 15).date,
            "isoweek": [14] * 15,
            "处理方式": ["A"] * 5 + ["B"] * 5 + ["C"] * 5,
            "单果重": [10, 11, 12, 11, 10, 20, 21, 22, 21, 20, 30, 31, 32, 31, 30],
        }
    )


def test_p_value_to_stars_uses_standard_thresholds() -> None:
    assert p_value_to_stars(0.0009) == "***"
    assert p_value_to_stars(0.009) == "**"
    assert p_value_to_stars(0.049) == "*"
    assert p_value_to_stars(0.05) == "ns"


def test_two_group_significance_runs_welch_ttest() -> None:
    result = analyze_significance(two_group_frame(), "单果重")
    row = result.significance.iloc[0]

    assert result.test_name == "Welch t-test"
    assert row["检验方法"] == "Welch t-test"
    assert row["组1"] == "对照"
    assert row["组2"] == "处理"
    assert row["组1样本量"] == 4
    assert row["组2样本量"] == 4
    assert row["p_value"] < 0.001
    assert row["显著性"] == "***"
    assert row["均值差"] == -10
    assert row["CI95%下限"] < row["均值差"] < row["CI95%上限"]
    assert row["CI95%上限"] < 0
    assert row["Hedges_g"] < -0.8
    assert row["效应量解释"] == "大效应"
    assert row["样本量判断"] == "样本量偏少"
    assert row["可信度判断"] == "中等"
    assert "建议增加重复后再确认" in row["结果建议"]


def test_multi_group_significance_runs_anova_and_tukey_with_letters() -> None:
    result = analyze_significance(multi_group_frame(), "单果重")

    assert result.test_name == "ANOVA + Tukey HSD"
    anova_row = result.significance.iloc[0]
    assert anova_row["检验方法"] == "one-way ANOVA"
    assert anova_row["eta_squared"] > 0.14
    assert anova_row["整体效应量解释"] == "整体大效应"
    assert anova_row["样本量判断"] == "样本量偏少"
    assert anova_row["可信度判断"] == "中等"
    assert "整体 ANOVA 显著" in anova_row["结果建议"]
    assert set(result.significance["检验方法"]) == {"one-way ANOVA", "Tukey HSD"}
    tukey_rows = result.significance.loc[result.significance["检验方法"] == "Tukey HSD"]
    assert {"CI95%下限", "CI95%上限", "Hedges_g", "可信度判断", "结果建议"}.issubset(tukey_rows.columns)
    assert tukey_rows["Hedges_g"].notna().all()
    assert tukey_rows["结果建议"].str.len().gt(0).all()
    assert set(result.annotations) == {"A", "B", "C"}
    for group_a in result.annotations:
        for group_b in result.annotations:
            if group_a >= group_b:
                continue
            assert set(result.annotations[group_a]).isdisjoint(result.annotations[group_b])


def test_tukey_letter_groups_prevents_significant_pairs_from_sharing_letters() -> None:
    letters = tukey_letter_groups(
        ["A", "B", "C"],
        {frozenset(("A", "C")), frozenset(("B", "C"))},
    )

    assert set(letters["A"]).intersection(letters["B"])
    assert set(letters["A"]).isdisjoint(letters["C"])
    assert set(letters["B"]).isdisjoint(letters["C"])


def test_significance_excludes_outliers_by_default() -> None:
    df = pd.DataFrame(
        {
            "序号": range(1, 9),
            "日期": pd.to_datetime(["2026-04-01"] * 8).date,
            "isoweek": [14] * 8,
            "处理方式": ["对照"] * 4 + ["处理"] * 4,
            "单果重": [10, 11, 12, 13, 20, 21, 22, 100],
        }
    )

    result = analyze_significance(df, "单果重")
    row = result.significance.iloc[0]

    assert len(result.outliers) == 1
    assert result.outliers.iloc[0]["序号"] == 8
    assert row["组2样本量"] == 3


def test_two_group_significance_plot_writes_stars_and_uses_expected_layout(tmp_path: Path) -> None:
    result = analyze_significance(two_group_frame(), "单果重")
    output = tmp_path / "two_group_significance.png"

    figure = plot_significance_summary(result, "单果重", output_path=output)
    ax = figure.axes[0]

    assert output.exists()
    assert output.stat().st_size > 0
    assert ax.get_xlim() == (0.0, 3.0)
    assert round(ax.patches[0].get_width(), 2) == 0.4
    assert any(text.get_text() == "***" for text in ax.texts)
    assert OUTLIER_NOTE in [text.get_text() for text in ax.texts]
    figure.clear()


def test_significance_plot_supports_sd_error_line(tmp_path: Path) -> None:
    result = analyze_significance(two_group_frame(), "单果重")
    output = tmp_path / "two_group_significance_sd.png"

    figure = plot_significance_summary(result, "单果重", error="sd", output_path=output)
    ax = figure.axes[0]
    labels = [text.get_text() for text in ax.texts]

    assert output.exists()
    assert output.stat().st_size > 0
    assert any("± 1.29" in label for label in labels)
    assert OUTLIER_NOTE in labels
    figure.clear()


def test_multi_group_significance_plot_writes_letters(tmp_path: Path) -> None:
    result = analyze_significance(multi_group_frame(), "单果重")
    output = tmp_path / "multi_group_significance.png"

    figure = plot_significance_summary(result, "单果重", output_path=output)
    ax = figure.axes[0]
    plotted_texts = {text.get_text() for text in ax.texts}

    assert output.exists()
    assert output.stat().st_size > 0
    assert round(ax.patches[0].get_width(), 2) == 0.4
    assert set(result.annotations.values()).issubset(plotted_texts)
    assert OUTLIER_NOTE in plotted_texts
    figure.clear()


def test_example_data_source_can_flow_through_module_three() -> None:
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
    parameter = detect_parameter_columns(formatted)[0]
    result = analyze_significance(formatted, parameter)

    assert result.test_name == "Welch t-test"
    assert not result.significance.empty
    assert "p_value" in result.significance.columns
