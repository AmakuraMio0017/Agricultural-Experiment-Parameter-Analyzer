from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


ID_COLUMN = "序号"
DATE_COLUMN = "日期"
WEEK_COLUMN = "isoweek"
TREATMENT_COLUMN = "处理方式"
FIXED_COLUMNS = (ID_COLUMN, DATE_COLUMN, WEEK_COLUMN, TREATMENT_COLUMN)
CONTROL_LABELS = ("对照", "CK", "Control")
OUTLIER_COLUMNS = (
    "参数",
    ID_COLUMN,
    DATE_COLUMN,
    WEEK_COLUMN,
    TREATMENT_COLUMN,
    "原始值",
    "下限",
    "上限",
    "判定规则",
)


class SummaryError(ValueError):
    pass


def detect_parameter_columns(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []

    fixed = set(FIXED_COLUMNS)
    parameters: list[str] = []
    for column in df.columns:
        column_name = str(column)
        if column_name in fixed:
            continue
        numeric = pd.to_numeric(df[column], errors="coerce")
        if numeric.notna().any():
            parameters.append(column_name)
    return parameters


def detect_outliers(
    df: pd.DataFrame,
    parameter: str,
    rule: str = "iqr",
    scope: str = "treatment",
) -> pd.DataFrame:
    _validate_summary_input(df, parameter)
    if rule != "iqr":
        raise SummaryError("离群值规则仅支持 iqr")
    if scope != "treatment":
        raise SummaryError("离群值识别范围仅支持 treatment")

    rows: list[dict[str, object]] = []
    working = df.copy()
    working[parameter] = pd.to_numeric(working[parameter], errors="coerce")
    for treatment, group in working.groupby(TREATMENT_COLUMN, sort=False):
        values = group[parameter].dropna()
        if values.empty:
            continue
        q1 = float(values.quantile(0.25))
        q3 = float(values.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_mask = (group[parameter] < lower) | (group[parameter] > upper)
        for _, row in group.loc[outlier_mask].iterrows():
            rows.append(
                {
                    "参数": parameter,
                    ID_COLUMN: row.get(ID_COLUMN, ""),
                    DATE_COLUMN: row.get(DATE_COLUMN, ""),
                    WEEK_COLUMN: row.get(WEEK_COLUMN, ""),
                    TREATMENT_COLUMN: treatment,
                    "原始值": row[parameter],
                    "下限": lower,
                    "上限": upper,
                    "判定规则": "组内 IQR 1.5倍",
                }
            )

    return pd.DataFrame(rows, columns=OUTLIER_COLUMNS)


def summarize_by_treatment(
    df: pd.DataFrame,
    parameter: str,
    control_labels: Iterable[str] | None = None,
    exclude_outliers: bool = True,
) -> pd.DataFrame:
    _validate_summary_input(df, parameter)
    working = df.copy()
    working[parameter] = pd.to_numeric(working[parameter], errors="coerce")

    if exclude_outliers:
        outliers = detect_outliers(working, parameter)
        if not outliers.empty:
            outlier_ids = set(outliers[ID_COLUMN].astype(str))
            working = working[~working[ID_COLUMN].astype(str).isin(outlier_ids)]

    working = working[[TREATMENT_COLUMN, parameter]].dropna(subset=[parameter])
    if working.empty:
        raise SummaryError(f"参数列没有可统计的数值：{parameter}")

    summary = (
        working.groupby(TREATMENT_COLUMN, sort=False)[parameter]
        .agg(n="count", mean="mean", sd="std", min="min", max="max")
        .reset_index()
    )
    summary["sem"] = summary["sd"] / np.sqrt(summary["n"])

    control_mean = _find_control_mean(summary, tuple(control_labels or CONTROL_LABELS))
    if control_mean is None or pd.isna(control_mean):
        summary["diff_vs_control"] = np.nan
        summary["diff_percent_vs_control"] = np.nan
    else:
        summary["diff_vs_control"] = summary["mean"] - control_mean
        if control_mean == 0:
            summary["diff_percent_vs_control"] = np.nan
        else:
            summary["diff_percent_vs_control"] = summary["diff_vs_control"] / control_mean * 100

    return summary[
        [
            TREATMENT_COLUMN,
            "n",
            "mean",
            "sd",
            "sem",
            "min",
            "max",
            "diff_vs_control",
            "diff_percent_vs_control",
        ]
    ]


def summarize_with_outliers(
    df: pd.DataFrame,
    parameter: str,
    control_labels: Iterable[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    outliers = detect_outliers(df, parameter)
    summary = summarize_by_treatment(df, parameter, control_labels=control_labels)
    return summary, outliers


def format_summary_for_output(summary_df: pd.DataFrame) -> pd.DataFrame:
    formatted = summary_df.copy()
    for column in formatted.columns:
        if column == "n":
            formatted[column] = formatted[column].astype("Int64")
            continue
        if pd.api.types.is_numeric_dtype(formatted[column]):
            formatted[column] = formatted[column].map(round_significant)
    return formatted


def format_outliers_for_output(outliers_df: pd.DataFrame) -> pd.DataFrame:
    formatted = outliers_df.copy()
    for column in ("原始值", "下限", "上限"):
        if column in formatted.columns:
            formatted[column] = pd.to_numeric(formatted[column], errors="coerce").map(round_significant)
    return formatted


def round_significant(value, digits: int = 3):
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, np.integer)):
        return int(value)
    number = float(value)
    if number == 0:
        return 0.0
    decimals = digits - int(np.floor(np.log10(abs(number)))) - 1
    return round(number, decimals)


def format_significant_text(value, digits: int = 3) -> str:
    rounded = round_significant(value, digits)
    if pd.isna(rounded):
        return ""
    return f"{rounded:g}"


def plot_treatment_summary(
    summary_df: pd.DataFrame,
    parameter: str,
    error: str = "sem",
    output_path: str | Path | None = None,
):
    if error not in {"sem", "sd"}:
        raise SummaryError("误差线类型仅支持 sem 或 sd")
    required = {TREATMENT_COLUMN, "mean", error}
    missing = required.difference(summary_df.columns)
    if missing:
        raise SummaryError(f"统计表缺少绘图列：{', '.join(sorted(missing))}")

    import matplotlib.pyplot as plt

    _configure_matplotlib_fonts(plt)
    labels = summary_df[TREATMENT_COLUMN].astype(str).tolist()
    means = summary_df["mean"].to_numpy(dtype=float)
    errors = summary_df[error].fillna(0).to_numpy(dtype=float)
    x_positions, x_limits = _bar_positions(len(labels))

    fig, ax = plt.subplots(figsize=(6.4, 4.8), dpi=300)
    ax.bar(
        x_positions,
        means,
        yerr=errors,
        width=0.4,
        capsize=4,
        color=_gray_palette(len(labels)),
        edgecolor="black",
        linewidth=0.8,
        error_kw={"elinewidth": 0.8, "capthick": 0.8},
    )
    label_padding = _label_padding(means, errors)
    _annotate_error_labels(ax, x_positions, means, errors, label_padding)
    ax.set_xlim(*x_limits)
    ax.set_ylim(*_padded_ylim(means, errors, label_padding))
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels)
    ax.set_ylabel(parameter)
    ax.set_xlabel(TREATMENT_COLUMN)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="0.88", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()

    if output_path is not None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=300, bbox_inches="tight")
    return fig


def _validate_summary_input(df: pd.DataFrame, parameter: str) -> None:
    if TREATMENT_COLUMN not in df.columns:
        raise SummaryError(f"缺少固定列：{TREATMENT_COLUMN}")
    if parameter not in df.columns:
        raise SummaryError(f"参数列不存在：{parameter}")


def _find_control_mean(summary: pd.DataFrame, control_labels: Iterable[str]) -> float | None:
    normalized = {str(label).strip().lower() for label in control_labels}
    for _, row in summary.iterrows():
        treatment = str(row[TREATMENT_COLUMN]).strip().lower()
        if treatment in normalized:
            return float(row["mean"])
    return None


def _padded_ylim(
    means: np.ndarray,
    errors: np.ndarray,
    label_padding: float = 0.0,
) -> tuple[float, float]:
    finite_means = means[np.isfinite(means)]
    finite_errors = np.nan_to_num(errors[np.isfinite(means)], nan=0.0)
    if finite_means.size == 0:
        return 0.0, 1.0
    lower = float(np.min(finite_means - finite_errors))
    upper = float(np.max(finite_means + finite_errors))
    span = upper - lower
    if span == 0:
        padding = max(abs(upper) * 0.2, 1.0)
    else:
        padding = span * 0.2
    return lower - padding, upper + padding + label_padding


def _bar_positions(count: int) -> tuple[np.ndarray, tuple[float, float]]:
    if count == 2:
        return np.array([1.0, 2.0]), (0.0, 3.0)
    if count <= 0:
        return np.array([]), (0.0, 1.0)
    positions = np.arange(1, count + 1, dtype=float)
    return positions, (0.0, float(count + 1))


def _annotate_error_labels(
    ax,
    positions: np.ndarray,
    means: np.ndarray,
    errors: np.ndarray,
    padding: float,
) -> None:
    for x_position, mean, error in zip(positions, means, errors):
        if not np.isfinite(mean):
            continue
        safe_error = 0.0 if not np.isfinite(error) else float(error)
        label = f"{format_significant_text(mean)} ± {format_significant_text(safe_error)}"
        ax.text(
            x_position,
            mean + safe_error + padding,
            label,
            ha="center",
            va="bottom",
            fontsize=8,
        )


def _label_padding(means: np.ndarray, errors: np.ndarray) -> float:
    finite_means = means[np.isfinite(means)]
    finite_errors = np.nan_to_num(errors[np.isfinite(means)], nan=0.0)
    if finite_means.size == 0:
        return 0.05
    lower = float(np.min(finite_means - finite_errors))
    upper = float(np.max(finite_means + finite_errors))
    span = upper - lower
    if span == 0:
        return max(abs(upper) * 0.03, 0.05)
    return span * 0.04


def _gray_palette(count: int) -> list[str]:
    if count <= 1:
        return ["0.65"]
    return [str(round(value, 3)) for value in np.linspace(0.35, 0.78, count)]


def _configure_matplotlib_fonts(plt) -> None:
    from matplotlib import font_manager

    candidates = (
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
    )
    available = {font.name for font in font_manager.fontManager.ttflist}
    for font_name in candidates:
        if font_name in available:
            plt.rcParams["font.sans-serif"] = [font_name, "DejaVu Sans"]
            break
    plt.rcParams["axes.unicode_minus"] = False
