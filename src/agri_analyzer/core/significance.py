from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.agri_analyzer.core.summary import (
    ID_COLUMN,
    REPLICATE_COLUMN,
    TREATMENT_COLUMN,
    SummaryError,
    _annotate_error_labels,
    _annotate_outlier_note,
    _bar_positions,
    _configure_matplotlib_fonts,
    _gray_palette,
    _label_padding,
    _padded_ylim,
    detect_outliers,
    format_significant_text,
    round_significant,
    summarize_by_treatment,
)


class SignificanceError(ValueError):
    pass


@dataclass(frozen=True)
class SignificanceResult:
    summary: pd.DataFrame
    significance: pd.DataFrame
    outliers: pd.DataFrame
    annotations: dict[str, str]
    test_name: str
    exclude_outliers: bool
    sample_scope: str


def p_value_to_stars(p_value: float) -> str:
    if pd.isna(p_value):
        return ""
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    if p_value < 0.05:
        return "*"
    return "ns"


def analyze_significance(
    df: pd.DataFrame,
    parameter: str,
    exclude_outliers: bool = True,
) -> SignificanceResult:
    _validate_input(df, parameter)
    outliers = detect_outliers(df, parameter) if exclude_outliers else pd.DataFrame()
    cleaned = _clean_for_parameter(df, parameter, outliers)
    prepared, sample_scope = _prepare_significance_samples(cleaned, parameter)
    groups = _group_values(prepared, parameter)
    if len(groups) < 2:
        raise SignificanceError("至少需要两个处理组才能进行显著性判断。")

    if sample_scope == "重复均值样本":
        summary = _summarize_prepared_by_treatment(prepared, parameter)
    else:
        summary = summarize_by_treatment(df, parameter, exclude_outliers=exclude_outliers)
    ordered_treatments = summary[TREATMENT_COLUMN].astype(str).tolist()
    ordered_groups = [(treatment, groups[treatment]) for treatment in ordered_treatments if treatment in groups]

    if len(ordered_groups) == 2:
        significance = _two_group_ttest(parameter, ordered_groups, summary)
        significance["样本口径"] = sample_scope
        annotations = {
            ordered_groups[0][0]: significance.loc[0, "显著性"],
            ordered_groups[1][0]: significance.loc[0, "显著性"],
        }
        return SignificanceResult(summary, significance, outliers, annotations, "Welch t-test", exclude_outliers, sample_scope)

    significance, letters = _multi_group_anova_tukey(parameter, ordered_groups, summary)
    significance["样本口径"] = sample_scope
    return SignificanceResult(summary, significance, outliers, letters, "ANOVA + Tukey HSD", exclude_outliers, sample_scope)


def format_significance_for_output(significance_df: pd.DataFrame) -> pd.DataFrame:
    formatted = significance_df.copy()
    integer_columns = {"组1样本量", "组2样本量", "样本量", "最小组样本量"}
    for column in formatted.columns:
        if column in integer_columns:
            formatted[column] = pd.to_numeric(formatted[column], errors="coerce").astype("Int64")
            continue
        if pd.api.types.is_numeric_dtype(formatted[column]):
            formatted[column] = formatted[column].map(round_significant)
    return formatted


def plot_significance_summary(
    result: SignificanceResult,
    parameter: str,
    error: str = "sem",
    output_path: str | Path | None = None,
):
    if error not in {"sem", "sd"}:
        raise SignificanceError("误差线类型仅支持 sem 或 sd")
    required = {TREATMENT_COLUMN, "mean", error}
    missing = required.difference(result.summary.columns)
    if missing:
        raise SignificanceError(f"统计表缺少绘图列：{', '.join(sorted(missing))}")

    import matplotlib.pyplot as plt

    _configure_matplotlib_fonts(plt)
    labels = result.summary[TREATMENT_COLUMN].astype(str).tolist()
    means = result.summary["mean"].to_numpy(dtype=float)
    errors = result.summary[error].fillna(0).to_numpy(dtype=float)
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
    if len(labels) == 2:
        _annotate_two_group_stars(ax, x_positions, means, errors, result.annotations, label_padding)
    else:
        _annotate_group_letters(ax, labels, x_positions, means, errors, result.annotations, label_padding)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels)
    ax.set_ylabel(parameter)
    ax.set_xlabel(TREATMENT_COLUMN)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="0.88", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    if result.exclude_outliers:
        _annotate_outlier_note(ax)

    if output_path is not None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=300, bbox_inches="tight")
    return fig


def _validate_input(df: pd.DataFrame, parameter: str) -> None:
    if TREATMENT_COLUMN not in df.columns:
        raise SignificanceError(f"缺少固定列：{TREATMENT_COLUMN}")
    if parameter not in df.columns:
        raise SignificanceError(f"参数列不存在：{parameter}")


def _clean_for_parameter(df: pd.DataFrame, parameter: str, outliers: pd.DataFrame) -> pd.DataFrame:
    working = df.copy()
    working[parameter] = pd.to_numeric(working[parameter], errors="coerce")
    if not outliers.empty and ID_COLUMN in outliers.columns and ID_COLUMN in working.columns:
        outlier_ids = set(outliers[ID_COLUMN].astype(str))
        working = working[~working[ID_COLUMN].astype(str).isin(outlier_ids)]
    columns = [TREATMENT_COLUMN]
    if REPLICATE_COLUMN in working.columns:
        columns.append(REPLICATE_COLUMN)
    columns.append(parameter)
    return working[columns].dropna(subset=[parameter])


def _prepare_significance_samples(df: pd.DataFrame, parameter: str) -> tuple[pd.DataFrame, str]:
    if REPLICATE_COLUMN not in df.columns:
        return df[[TREATMENT_COLUMN, parameter]].copy(), "逐行样本"

    working = df[[TREATMENT_COLUMN, REPLICATE_COLUMN, parameter]].copy()
    working[REPLICATE_COLUMN] = working[REPLICATE_COLUMN].astype(str)
    working = working[working[REPLICATE_COLUMN].str.strip() != ""]
    if working.empty:
        return df[[TREATMENT_COLUMN, parameter]].copy(), "逐行样本"

    prepared = (
        working.groupby([TREATMENT_COLUMN, REPLICATE_COLUMN], sort=False)[parameter]
        .mean()
        .reset_index()
    )
    return prepared[[TREATMENT_COLUMN, parameter]], "重复均值样本"


def _summarize_prepared_by_treatment(df: pd.DataFrame, parameter: str) -> pd.DataFrame:
    summary = (
        df.groupby(TREATMENT_COLUMN, sort=False)[parameter]
        .agg(n="count", sum="sum", mean="mean", sd="std", min="min", max="max")
        .reset_index()
    )
    summary["sem"] = summary["sd"] / np.sqrt(summary["n"])
    summary["sum_diff_vs_control"] = np.nan
    summary["sum_diff_percent_vs_control"] = np.nan
    summary["diff_vs_control"] = np.nan
    summary["diff_percent_vs_control"] = np.nan
    return summary[
        [
            TREATMENT_COLUMN,
            "n",
            "sum",
            "mean",
            "sd",
            "sem",
            "min",
            "max",
            "sum_diff_vs_control",
            "sum_diff_percent_vs_control",
            "diff_vs_control",
            "diff_percent_vs_control",
        ]
    ]


def _group_values(df: pd.DataFrame, parameter: str) -> dict[str, np.ndarray]:
    groups: dict[str, np.ndarray] = {}
    for treatment, group in df.groupby(TREATMENT_COLUMN, sort=False):
        values = pd.to_numeric(group[parameter], errors="coerce").dropna().to_numpy(dtype=float)
        if len(values) > 0:
            groups[str(treatment)] = values
    return groups


def _two_group_ttest(
    parameter: str,
    groups: list[tuple[str, np.ndarray]],
    summary: pd.DataFrame,
) -> pd.DataFrame:
    (group_a, values_a), (group_b, values_b) = groups
    if len(values_a) < 2 or len(values_b) < 2:
        raise SignificanceError("Welch t-test 要求每个处理组至少有 2 个有效数值。")
    test = stats.ttest_ind(values_a, values_b, equal_var=False, nan_policy="omit")
    p_value = float(test.pvalue)
    row_a = _summary_row(summary, group_a)
    row_b = _summary_row(summary, group_b)
    mean_diff = float(row_a["mean"] - row_b["mean"])
    welch_df = _welch_df(values_a, values_b)
    ci_low, ci_high = _welch_ci95(values_a, values_b, mean_diff, welch_df)
    hedges_g = _hedges_g(values_a, values_b)
    effect_label = _pair_effect_label(hedges_g)
    sample_label = _sample_size_label(len(values_a), len(values_b))
    confidence = _pair_confidence_label(
        p_value,
        ci_low,
        ci_high,
        effect_label,
        sample_label,
    )
    advice = _pair_result_advice(
        group_a,
        group_b,
        p_value,
        ci_low,
        ci_high,
        effect_label,
        sample_label,
        confidence,
    )
    return pd.DataFrame(
        [
            {
                "参数": parameter,
                "比较范围": "整体",
                "检验方法": "Welch t-test",
                "组1": group_a,
                "组2": group_b,
                "组1样本量": int(row_a["n"]),
                "组2样本量": int(row_b["n"]),
                "组1均值": row_a["mean"],
                "组2均值": row_b["mean"],
                "组1SEM": row_a["sem"],
                "组2SEM": row_b["sem"],
                "组1SD": row_a["sd"],
                "组2SD": row_b["sd"],
                "statistic": float(test.statistic),
                "p_value": p_value,
                "显著性": p_value_to_stars(p_value),
                "均值差": mean_diff,
                "Welch_df": welch_df,
                "CI95%下限": ci_low,
                "CI95%上限": ci_high,
                "Hedges_g": hedges_g,
                "效应量解释": effect_label,
                "eta_squared": np.nan,
                "整体效应量解释": "",
                "最小组样本量": min(len(values_a), len(values_b)),
                "样本量判断": sample_label,
                "可信度判断": confidence,
                "结果建议": advice,
            }
        ]
    )


def _multi_group_anova_tukey(
    parameter: str,
    groups: list[tuple[str, np.ndarray]],
    summary: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, str]]:
    small_groups = [name for name, values in groups if len(values) < 2]
    if small_groups:
        raise SignificanceError(f"ANOVA 要求每个处理组至少有 2 个有效数值：{', '.join(small_groups)}")

    names = [name for name, _ in groups]
    values = [values for _, values in groups]
    anova = stats.f_oneway(*values)
    tukey = stats.tukey_hsd(*values)
    tukey_ci_low, tukey_ci_high = _tukey_ci95(tukey, len(names))
    eta_squared = _eta_squared(values)
    min_group_size = min(len(item) for item in values)
    anova_sample_label = _sample_size_label(*[len(item) for item in values])
    anova_effect_label = _anova_effect_label(eta_squared)
    anova_confidence = _anova_confidence_label(
        float(anova.pvalue),
        eta_squared,
        anova_sample_label,
    )
    anova_advice = _anova_result_advice(
        float(anova.pvalue),
        anova_effect_label,
        anova_sample_label,
        anova_confidence,
    )
    rows: list[dict[str, object]] = [
        {
            "参数": parameter,
            "比较范围": "整体",
            "检验方法": "one-way ANOVA",
            "组1": "全部处理",
            "组2": "",
            "组1样本量": int(sum(len(item) for item in values)),
            "组2样本量": pd.NA,
            "组1均值": np.nan,
            "组2均值": np.nan,
            "组1SEM": np.nan,
            "组2SEM": np.nan,
            "组1SD": np.nan,
            "组2SD": np.nan,
            "statistic": float(anova.statistic),
            "p_value": float(anova.pvalue),
            "显著性": p_value_to_stars(float(anova.pvalue)),
            "均值差": np.nan,
            "Welch_df": np.nan,
            "CI95%下限": np.nan,
            "CI95%上限": np.nan,
            "Hedges_g": np.nan,
            "效应量解释": "",
            "eta_squared": eta_squared,
            "整体效应量解释": anova_effect_label,
            "最小组样本量": min_group_size,
            "样本量判断": anova_sample_label,
            "可信度判断": anova_confidence,
            "结果建议": anova_advice,
        }
    ]

    significant_pairs: set[frozenset[str]] = set()
    for i, group_a in enumerate(names):
        for j in range(i + 1, len(names)):
            group_b = names[j]
            p_value = float(tukey.pvalue[i, j])
            if p_value < 0.05:
                significant_pairs.add(frozenset((group_a, group_b)))
            row_a = _summary_row(summary, group_a)
            row_b = _summary_row(summary, group_b)
            mean_diff = float(row_a["mean"] - row_b["mean"])
            hedges_g = _hedges_g(groups[i][1], groups[j][1])
            effect_label = _pair_effect_label(hedges_g)
            sample_label = _sample_size_label(len(groups[i][1]), len(groups[j][1]))
            ci_low = float(tukey_ci_low[i, j])
            ci_high = float(tukey_ci_high[i, j])
            confidence = _pair_confidence_label(
                p_value,
                ci_low,
                ci_high,
                effect_label,
                sample_label,
            )
            advice = _pair_result_advice(
                group_a,
                group_b,
                p_value,
                ci_low,
                ci_high,
                effect_label,
                sample_label,
                confidence,
            )
            rows.append(
                {
                    "参数": parameter,
                    "比较范围": "整体",
                    "检验方法": "Tukey HSD",
                    "组1": group_a,
                    "组2": group_b,
                    "组1样本量": int(row_a["n"]),
                    "组2样本量": int(row_b["n"]),
                    "组1均值": row_a["mean"],
                    "组2均值": row_b["mean"],
                    "组1SEM": row_a["sem"],
                    "组2SEM": row_b["sem"],
                    "组1SD": row_a["sd"],
                    "组2SD": row_b["sd"],
                    "statistic": float(tukey.statistic[i, j]),
                    "p_value": p_value,
                    "显著性": p_value_to_stars(p_value),
                    "均值差": mean_diff,
                    "Welch_df": np.nan,
                    "CI95%下限": ci_low,
                    "CI95%上限": ci_high,
                    "Hedges_g": hedges_g,
                    "效应量解释": effect_label,
                    "eta_squared": np.nan,
                    "整体效应量解释": "",
                    "最小组样本量": min(len(groups[i][1]), len(groups[j][1])),
                    "样本量判断": sample_label,
                    "可信度判断": confidence,
                    "结果建议": advice,
                }
            )

    letters = tukey_letter_groups(names, significant_pairs)
    return pd.DataFrame(rows), letters


def tukey_letter_groups(
    treatment_names: list[str],
    significant_pairs: set[frozenset[str]],
) -> dict[str, str]:
    letters: list[set[str]] = []
    assignments: dict[str, list[str]] = {name: [] for name in treatment_names}
    alphabet = list("abcdefghijklmnopqrstuvwxyz")

    for treatment in treatment_names:
        for index, members in enumerate(letters):
            if all(frozenset((treatment, member)) not in significant_pairs for member in members):
                members.add(treatment)
                assignments[treatment].append(alphabet[index])
        if not assignments[treatment]:
            letters.append({treatment})
            assignments[treatment].append(alphabet[len(letters) - 1])

    return {name: "".join(assignments[name]) for name in treatment_names}


def _summary_row(summary: pd.DataFrame, treatment: str) -> pd.Series:
    row = summary.loc[summary[TREATMENT_COLUMN].astype(str) == treatment]
    if row.empty:
        raise SignificanceError(f"统计摘要中缺少处理组：{treatment}")
    return row.iloc[0]


def _welch_df(values_a: np.ndarray, values_b: np.ndarray) -> float:
    n_a = len(values_a)
    n_b = len(values_b)
    var_a = float(np.var(values_a, ddof=1))
    var_b = float(np.var(values_b, ddof=1))
    term_a = var_a / n_a
    term_b = var_b / n_b
    numerator = (term_a + term_b) ** 2
    denominator = (term_a**2 / (n_a - 1)) + (term_b**2 / (n_b - 1))
    if denominator == 0:
        return np.nan
    return numerator / denominator


def _welch_ci95(values_a: np.ndarray, values_b: np.ndarray, mean_diff: float, welch_df: float) -> tuple[float, float]:
    if not np.isfinite(welch_df):
        return np.nan, np.nan
    se = np.sqrt(np.var(values_a, ddof=1) / len(values_a) + np.var(values_b, ddof=1) / len(values_b))
    critical = stats.t.ppf(0.975, welch_df)
    margin = float(critical * se)
    return mean_diff - margin, mean_diff + margin


def _tukey_ci95(tukey_result, group_count: int) -> tuple[np.ndarray, np.ndarray]:
    try:
        interval = tukey_result.confidence_interval(confidence_level=0.95)
        return np.asarray(interval.low, dtype=float), np.asarray(interval.high, dtype=float)
    except (AttributeError, TypeError, ValueError):
        empty = np.full((group_count, group_count), np.nan)
        return empty, empty


def _hedges_g(values_a: np.ndarray, values_b: np.ndarray) -> float:
    n_a = len(values_a)
    n_b = len(values_b)
    pooled_denominator = n_a + n_b - 2
    if pooled_denominator <= 0:
        return np.nan
    pooled_sd = np.sqrt(
        ((n_a - 1) * np.var(values_a, ddof=1) + (n_b - 1) * np.var(values_b, ddof=1)) / pooled_denominator
    )
    mean_diff = float(np.mean(values_a) - np.mean(values_b))
    if pooled_sd == 0:
        if mean_diff == 0:
            return 0.0
        return float(np.sign(mean_diff) * np.inf)
    correction = 1 - 3 / (4 * (n_a + n_b) - 9)
    return float((mean_diff / pooled_sd) * correction)


def _eta_squared(groups: list[np.ndarray]) -> float:
    all_values = np.concatenate(groups)
    grand_mean = float(np.mean(all_values))
    ss_between = sum(len(values) * (float(np.mean(values)) - grand_mean) ** 2 for values in groups)
    ss_total = float(np.sum((all_values - grand_mean) ** 2))
    if ss_total == 0:
        return np.nan
    return float(ss_between / ss_total)


def _sample_size_label(*sizes: int) -> str:
    min_size = min(sizes)
    if min_size < 3:
        return "样本量不足"
    if min_size < 6:
        return "样本量偏少"
    if min_size < 10:
        return "样本量基本可接受"
    return "样本量较好"


def _pair_effect_label(hedges_g: float) -> str:
    if not np.isfinite(hedges_g):
        return "无法判断"
    absolute = abs(hedges_g)
    if absolute < 0.2:
        return "差异很小"
    if absolute < 0.5:
        return "小效应"
    if absolute < 0.8:
        return "中等效应"
    return "大效应"


def _anova_effect_label(eta_squared: float) -> str:
    if not np.isfinite(eta_squared):
        return "无法判断"
    if eta_squared < 0.01:
        return "整体效应很小"
    if eta_squared < 0.06:
        return "整体小效应"
    if eta_squared < 0.14:
        return "整体中等效应"
    return "整体大效应"


def _ci_crosses_zero(ci_low: float, ci_high: float) -> bool:
    if not np.isfinite(ci_low) or not np.isfinite(ci_high):
        return True
    return ci_low <= 0 <= ci_high


def _pair_confidence_label(
    p_value: float,
    ci_low: float,
    ci_high: float,
    effect_label: str,
    sample_label: str,
) -> str:
    if p_value >= 0.05:
        return "不支持显著差异"
    if sample_label == "样本量不足":
        return "较低"
    if _ci_crosses_zero(ci_low, ci_high):
        return "较低"
    if effect_label in {"中等效应", "大效应"} and sample_label in {"样本量基本可接受", "样本量较好"}:
        return "较高"
    if sample_label == "样本量偏少" or effect_label in {"差异很小", "小效应"}:
        return "中等"
    return "中等"


def _anova_confidence_label(p_value: float, eta_squared: float, sample_label: str) -> str:
    if p_value >= 0.05:
        return "不支持显著差异"
    if sample_label == "样本量不足":
        return "较低"
    if not np.isfinite(eta_squared) or eta_squared < 0.01:
        return "较低"
    if eta_squared >= 0.06 and sample_label in {"样本量基本可接受", "样本量较好"}:
        return "较高"
    return "中等"


def _pair_result_advice(
    group_a: str,
    group_b: str,
    p_value: float,
    ci_low: float,
    ci_high: float,
    effect_label: str,
    sample_label: str,
    confidence: str,
) -> str:
    if p_value >= 0.05:
        return f"{group_a} 与 {group_b} 未检测到显著差异，当前数据不支持两组均值存在稳定差异。"
    if confidence == "较高":
        return f"{group_a} 与 {group_b} 差异显著，CI95%未跨0，效应量为{effect_label}，{sample_label}，结果可信度较高。"
    if sample_label in {"样本量不足", "样本量偏少"}:
        return f"{group_a} 与 {group_b} 差异显著，但{sample_label}，建议增加重复后再确认。"
    if _ci_crosses_zero(ci_low, ci_high):
        return f"{group_a} 与 {group_b} 差异显著，但CI95%跨0，差异稳定性不足，建议谨慎解释。"
    return f"{group_a} 与 {group_b} 差异显著，效应量为{effect_label}，建议结合试验设计和实际生产意义综合判断。"


def _anova_result_advice(
    p_value: float,
    effect_label: str,
    sample_label: str,
    confidence: str,
) -> str:
    if p_value >= 0.05:
        return "整体 ANOVA 未检测到显著差异，当前数据不支持全部处理之间存在稳定差异。"
    if confidence == "较高":
        return f"整体 ANOVA 显著，{effect_label}，{sample_label}，说明处理方式对该参数的影响较稳定。"
    if sample_label in {"样本量不足", "样本量偏少"}:
        return f"整体 ANOVA 显著，但{sample_label}，建议增加重复后再确认。"
    return f"整体 ANOVA 显著，{effect_label}，建议继续查看 Tukey HSD 两两比较结果。"


def _annotate_two_group_stars(
    ax,
    positions: np.ndarray,
    means: np.ndarray,
    errors: np.ndarray,
    annotations: dict[str, str],
    label_padding: float,
) -> None:
    if len(positions) != 2:
        return
    star = next((value for value in annotations.values() if value), "")
    if not star:
        return
    tops = means + np.nan_to_num(errors, nan=0.0)
    y_base = float(np.nanmax(tops)) + label_padding * 4
    y_tick = y_base + label_padding
    ax.plot(
        [positions[0], positions[0], positions[1], positions[1]],
        [y_base, y_tick, y_tick, y_base],
        color="black",
        linewidth=0.8,
    )
    ax.text(np.mean(positions), y_tick + label_padding, star, ha="center", va="bottom", fontsize=10)
    lower, upper = ax.get_ylim()
    ax.set_ylim(lower, max(upper, y_tick + label_padding * 5))


def _annotate_group_letters(
    ax,
    labels: list[str],
    positions: np.ndarray,
    means: np.ndarray,
    errors: np.ndarray,
    annotations: dict[str, str],
    label_padding: float,
) -> None:
    highest = ax.get_ylim()[1]
    for label, x_position, mean, error in zip(labels, positions, means, errors):
        if not np.isfinite(mean):
            continue
        text = annotations.get(label, "")
        if not text:
            continue
        y_position = mean + (0.0 if not np.isfinite(error) else float(error)) + label_padding * 5
        highest = max(highest, y_position + label_padding * 3)
        ax.text(x_position, y_position, text, ha="center", va="bottom", fontsize=10)
    lower, upper = ax.get_ylim()
    ax.set_ylim(lower, max(upper, highest))
