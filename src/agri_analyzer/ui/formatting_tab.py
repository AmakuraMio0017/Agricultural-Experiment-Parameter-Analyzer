from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from src.agri_analyzer.core.formatting import (
    ColumnDetectionError,
    TableReadError,
    detect_columns,
    format_parameters,
    read_table,
)
from src.agri_analyzer.models.pandas_table_model import PandasTableModel
from src.agri_analyzer.ui.column_dialog import ColumnConfirmDialog


class FormattingTab(QWidget):
    formatting_completed = Signal(pd.DataFrame)

    def __init__(self) -> None:
        super().__init__()
        self.source_df: pd.DataFrame | None = None
        self.formatted_df: pd.DataFrame | None = None
        self.source_path: Path | None = None

        self.status_label = QLabel("步骤 1：导入 Excel 或 CSV 文件")
        self.status_label.setAlignment(Qt.AlignLeft)
        self.import_button = QPushButton("导入文件")
        self.format_button = QPushButton("确认列并格式化")
        self.export_button = QPushButton("导出 XLSX")
        self.format_button.setEnabled(False)
        self.export_button.setEnabled(False)

        self.table_model = PandasTableModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(False)

        copy_action = QAction("复制", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.copy_selection)
        self.table_view.addAction(copy_action)
        self.table_view.setContextMenuPolicy(Qt.ActionsContextMenu)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.import_button)
        top_layout.addWidget(self.format_button)
        top_layout.addWidget(self.export_button)
        top_layout.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addLayout(top_layout)
        layout.addWidget(self.table_view)

        self.import_button.clicked.connect(self.import_file)
        self.format_button.clicked.connect(self.confirm_and_format)
        self.export_button.clicked.connect(self.export_file)

    def import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择数据文件",
            "",
            "数据文件 (*.xlsx *.xls *.csv)",
        )
        if not path:
            return

        try:
            self.source_df = read_table(path)
        except TableReadError as exc:
            QMessageBox.critical(self, "文件解析失败", str(exc))
            return

        self.source_path = Path(path)
        self.formatted_df = None
        self.table_model.set_dataframe(self.source_df)
        self.table_view.resizeColumnsToContents()
        self.status_label.setText(f"步骤 2：已导入 {self.source_path.name}，请确认列识别并格式化")
        self.format_button.setEnabled(True)
        self.export_button.setEnabled(False)

    def confirm_and_format(self) -> None:
        if self.source_df is None:
            QMessageBox.warning(self, "未导入文件", "请先导入 Excel 或 CSV 文件。")
            return

        try:
            detection = detect_columns(self.source_df)
        except ColumnDetectionError as exc:
            QMessageBox.warning(self, "列识别失败", str(exc))
            return

        columns = [str(column) for column in self.source_df.columns]
        dialog = ColumnConfirmDialog(columns, detection, self)
        if dialog.exec() != dialog.Accepted:
            return

        date_column, treatment_column, parameter_columns = dialog.selected_columns()
        try:
            self.formatted_df = format_parameters(
                self.source_df,
                date_column,
                treatment_column,
                parameter_columns,
            )
        except ColumnDetectionError as exc:
            QMessageBox.warning(self, "格式化失败", str(exc))
            return

        self.table_model.set_dataframe(self.formatted_df)
        self.table_view.resizeColumnsToContents()
        self.status_label.setText("步骤 3：格式化完成，可预览、复制或导出 XLSX")
        self.export_button.setEnabled(True)
        self.formatting_completed.emit(self.formatted_df)

    def export_file(self) -> None:
        if self.formatted_df is None:
            QMessageBox.warning(self, "无可导出数据", "请先完成格式化。")
            return

        default_name = "formatted_parameters.xlsx"
        if self.source_path:
            default_name = f"{self.source_path.stem}_formatted.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出格式化结果",
            str(Path("outputs") / default_name),
            "Excel 文件 (*.xlsx)",
        )
        if not path:
            return

        try:
            output_path = Path(path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self.formatted_df.to_excel(output_path, index=False)
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", f"导出 XLSX 失败：{exc}")
            return

        QMessageBox.information(self, "导出完成", f"已导出到：{output_path}")

    def copy_selection(self) -> None:
        indexes = self.table_view.selectionModel().selectedIndexes()
        if not indexes:
            return
        indexes = sorted(indexes, key=lambda index: (index.row(), index.column()))
        rows: dict[int, list[str]] = {}
        for index in indexes:
            rows.setdefault(index.row(), []).append(str(index.data() or ""))
        text = "\n".join("\t".join(values) for _, values in sorted(rows.items()))
        QApplication.clipboard().setText(text)
