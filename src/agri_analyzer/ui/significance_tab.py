from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from src.agri_analyzer.core.significance import (
    SignificanceError,
    SignificanceResult,
    analyze_significance,
    format_significance_for_output,
    plot_significance_summary,
)
from src.agri_analyzer.core.summary import (
    detect_parameter_columns,
    format_outliers_for_output,
    format_summary_for_output,
)
from src.agri_analyzer.models.pandas_table_model import PandasTableModel


class SignificanceTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.formatted_df: pd.DataFrame | None = None
        self.result: SignificanceResult | None = None

        self.status_label = QLabel("请先在模块一完成参数格式化。")
        self.status_label.setAlignment(Qt.AlignLeft)

        self.parameter_combo = QComboBox()
        self.parameter_combo.setEnabled(False)
        self.error_combo = QComboBox()
        self.error_combo.addItems(["SEM", "SD"])
        self.error_combo.setEnabled(False)

        self.refresh_button = QPushButton("生成显著性结果")
        self.export_table_button = QPushButton("导出结果 XLSX")
        self.export_plot_button = QPushButton("导出图表")
        self.refresh_button.setEnabled(False)
        self.export_table_button.setEnabled(False)
        self.export_plot_button.setEnabled(False)

        self.table_model = PandasTableModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(False)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("参数"))
        top_layout.addWidget(self.parameter_combo)
        top_layout.addWidget(QLabel("误差线"))
        top_layout.addWidget(self.error_combo)
        top_layout.addWidget(self.refresh_button)
        top_layout.addWidget(self.export_table_button)
        top_layout.addWidget(self.export_plot_button)
        top_layout.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addLayout(top_layout)
        layout.addWidget(self.table_view)

        self.parameter_combo.currentTextChanged.connect(self.refresh_significance)
        self.refresh_button.clicked.connect(self.refresh_significance)
        self.export_table_button.clicked.connect(self.export_table)
        self.export_plot_button.clicked.connect(self.export_plot)

    def set_formatted_data(self, dataframe: pd.DataFrame) -> None:
        self.formatted_df = dataframe.copy()
        parameters = detect_parameter_columns(self.formatted_df)
        self.parameter_combo.blockSignals(True)
        self.parameter_combo.clear()
        self.parameter_combo.addItems(parameters)
        self.parameter_combo.blockSignals(False)

        has_parameters = bool(parameters)
        self.parameter_combo.setEnabled(has_parameters)
        self.error_combo.setEnabled(has_parameters)
        self.refresh_button.setEnabled(has_parameters)
        self.export_table_button.setEnabled(False)
        self.export_plot_button.setEnabled(False)

        if not has_parameters:
            self.result = None
            self.table_model.set_dataframe(pd.DataFrame())
            self.status_label.setText("模块一结果中没有可用于显著性判断的数值参数列。")
            return

        self.status_label.setText("已接收模块一格式化结果，可生成显著性判断。")
        self.refresh_significance()

    def refresh_significance(self) -> None:
        if self.formatted_df is None or not self.parameter_combo.currentText():
            return

        parameter = self.parameter_combo.currentText()
        try:
            self.result = analyze_significance(self.formatted_df, parameter)
        except SignificanceError as exc:
            self.result = None
            self.table_model.set_dataframe(pd.DataFrame())
            self.export_table_button.setEnabled(False)
            self.export_plot_button.setEnabled(False)
            QMessageBox.warning(self, "显著性判断失败", str(exc))
            return

        preview = format_significance_for_output(self.result.significance)
        self.table_model.set_dataframe(preview)
        self.table_view.resizeColumnsToContents()
        outlier_count = 0 if self.result.outliers is None else len(self.result.outliers)
        self.status_label.setText(
            f"已生成参数“{parameter}”的显著性判断：{self.result.test_name}，已剔除离群值 {outlier_count} 个。"
        )
        self.export_table_button.setEnabled(True)
        self.export_plot_button.setEnabled(True)

    def export_table(self) -> None:
        if self.result is None:
            QMessageBox.warning(self, "无可导出数据", "请先生成显著性结果。")
            return

        parameter = self.parameter_combo.currentText() or "significance"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出显著性结果",
            str(Path("outputs") / f"{parameter}_significance.xlsx"),
            "Excel 文件 (*.xlsx)",
        )
        if not path:
            return

        try:
            output_path = Path(path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with pd.ExcelWriter(output_path) as writer:
                format_summary_for_output(self.result.summary).to_excel(
                    writer,
                    sheet_name="summary",
                    index=False,
                )
                format_significance_for_output(self.result.significance).to_excel(
                    writer,
                    sheet_name="significance",
                    index=False,
                )
                format_outliers_for_output(self.result.outliers).to_excel(
                    writer,
                    sheet_name="outliers",
                    index=False,
                )
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", f"导出显著性结果失败：{exc}")
            return

        QMessageBox.information(self, "导出完成", f"已导出到：{output_path}")

    def export_plot(self) -> None:
        if self.result is None:
            QMessageBox.warning(self, "无可导出图表", "请先生成显著性结果。")
            return

        parameter = self.parameter_combo.currentText() or "significance"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出显著性图表",
            str(Path("outputs") / f"{parameter}_significance.png"),
            "PNG 图片 (*.png);;PDF 文件 (*.pdf);;TIFF 图片 (*.tif *.tiff)",
        )
        if not path:
            return

        try:
            figure = plot_significance_summary(
                self.result,
                parameter,
                error=self.error_combo.currentText().lower(),
                output_path=path,
            )
            figure.clear()
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", f"导出显著性图表失败：{exc}")
            return

        QMessageBox.information(self, "导出完成", f"已导出到：{Path(path)}")
