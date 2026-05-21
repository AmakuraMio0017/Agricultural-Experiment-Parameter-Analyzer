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

from src.agri_analyzer.core.summary import (
    SummaryError,
    detect_parameter_columns,
    plot_treatment_summary,
    summarize_by_treatment,
)
from src.agri_analyzer.models.pandas_table_model import PandasTableModel


class SummaryTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.formatted_df: pd.DataFrame | None = None
        self.summary_df: pd.DataFrame | None = None

        self.status_label = QLabel("请先在模块一完成参数格式化。")
        self.status_label.setAlignment(Qt.AlignLeft)

        self.parameter_combo = QComboBox()
        self.parameter_combo.setEnabled(False)
        self.error_combo = QComboBox()
        self.error_combo.addItems(["SEM", "SD"])
        self.error_combo.setEnabled(False)

        self.refresh_button = QPushButton("生成统计表")
        self.export_table_button = QPushButton("导出统计表 XLSX")
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

        self.parameter_combo.currentTextChanged.connect(self.refresh_summary)
        self.refresh_button.clicked.connect(self.refresh_summary)
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
            self.summary_df = None
            self.table_model.set_dataframe(pd.DataFrame())
            self.status_label.setText("模块一结果中没有可统计的数值参数列。")
            return

        self.status_label.setText("已接收模块一格式化结果，可生成数据情况统计。")
        self.refresh_summary()

    def refresh_summary(self) -> None:
        if self.formatted_df is None or not self.parameter_combo.currentText():
            return

        parameter = self.parameter_combo.currentText()
        try:
            self.summary_df = summarize_by_treatment(self.formatted_df, parameter)
        except SummaryError as exc:
            QMessageBox.warning(self, "统计失败", str(exc))
            return

        preview = self.summary_df.copy()
        numeric_columns = preview.select_dtypes(include="number").columns
        preview[numeric_columns] = preview[numeric_columns].round(4)
        self.table_model.set_dataframe(preview)
        self.table_view.resizeColumnsToContents()
        self.status_label.setText(f"已生成参数“{parameter}”的数据情况统计。")
        self.export_table_button.setEnabled(True)
        self.export_plot_button.setEnabled(True)

    def export_table(self) -> None:
        if self.summary_df is None:
            QMessageBox.warning(self, "无可导出数据", "请先生成统计表。")
            return

        parameter = self.parameter_combo.currentText() or "summary"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出统计表",
            str(Path("outputs") / f"{parameter}_summary.xlsx"),
            "Excel 文件 (*.xlsx)",
        )
        if not path:
            return

        try:
            output_path = Path(path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self.summary_df.to_excel(output_path, index=False)
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", f"导出统计表失败：{exc}")
            return

        QMessageBox.information(self, "导出完成", f"已导出到：{output_path}")

    def export_plot(self) -> None:
        if self.summary_df is None:
            QMessageBox.warning(self, "无可导出图表", "请先生成统计表。")
            return

        parameter = self.parameter_combo.currentText() or "summary"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出图表",
            str(Path("outputs") / f"{parameter}_summary.png"),
            "PNG 图片 (*.png);;PDF 文件 (*.pdf);;TIFF 图片 (*.tif *.tiff)",
        )
        if not path:
            return

        try:
            figure = plot_treatment_summary(
                self.summary_df,
                parameter,
                error=self.error_combo.currentText().lower(),
                output_path=path,
            )
            figure.clear()
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", f"导出图表失败：{exc}")
            return

        QMessageBox.information(self, "导出完成", f"已导出到：{Path(path)}")
