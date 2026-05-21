from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


FIXED_COLUMNS = ("序号", "日期", "isoweek", "处理方式")
CONTROL_LABELS = ("对照", "CK", "Control")
TREATMENT_COLUMN = "处理方式"


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


def summarize_by_treatment(
    df: pd.DataFrame,
    parameter: str,
    control_labels: Iterable[str] | None = None,
) -> pd.DataFrame:
    if TREATMENT_COLUMN not in df.columns:
        raise SummaryError(f"缺少固定列：{TREATMENT_COLUMN}")
    if parameter not in df.columns:
        raise SummaryError(f"参数列不存在：{parameter}")

    working = pd.DataFrame(
        {
            TREATMENT_COLUMN: df[TREATMENT_COLUMN].astype(str),
            parameter: pd.to_numeric(df[parameter], errors="coerce"),
        }
    ).dropna(subset=[parameter])
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
    x_positions = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(6.4, 4.8), dpi=300)
    ax.bar(
        x_positions,
        means,
        yerr=errors,
        capsize=4,
        color=_gray_palette(len(labels)),
        edgecolor="black",
        linewidth=0.8,
        error_kw={"elinewidth": 0.8, "capthick": 0.8},
    )
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


def _find_control_mean(summary: pd.DataFrame, control_labels: Iterable[str]) -> float | None:
    normalized = {str(label).strip().lower() for label in control_labels}
    for _, row in summary.iterrows():
        treatment = str(row[TREATMENT_COLUMN]).strip().lower()
        if treatment in normalized:
            return float(row["mean"])
    return None


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
