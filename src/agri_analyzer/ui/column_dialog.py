from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.agri_analyzer.core.formatting import ColumnDetection


class ColumnConfirmDialog(QDialog):
    def __init__(self, columns: list[str], detection: ColumnDetection, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("确认列识别结果")
        self.resize(520, 420)

        self.date_combo = QComboBox()
        self.date_combo.addItems(columns)
        self.treatment_combo = QComboBox()
        self.treatment_combo.addItems(columns)

        if detection.date_column in columns:
            self.date_combo.setCurrentText(detection.date_column)
        if detection.treatment_column in columns:
            self.treatment_combo.setCurrentText(detection.treatment_column)

        self.parameter_checks: list[QCheckBox] = []
        parameter_box = QGroupBox("选择需要保留的植株参数")
        parameter_layout = QVBoxLayout(parameter_box)
        for column in columns:
            check = QCheckBox(column)
            check.setChecked(column in detection.parameter_columns)
            self.parameter_checks.append(check)
            parameter_layout.addWidget(check)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.addWidget(parameter_box)
        scroll.setWidget(holder)

        message = "请确认自动识别结果。"
        if detection.messages:
            message += "\n" + "\n".join(detection.messages)

        form = QFormLayout()
        form.addRow("日期列", self.date_combo)
        form.addRow("处理方式列", self.treatment_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(message))
        layout.addLayout(form)
        layout.addWidget(scroll)
        layout.addWidget(buttons)

    def selected_columns(self) -> tuple[str, str, list[str]]:
        parameters = [check.text() for check in self.parameter_checks if check.isChecked()]
        return self.date_combo.currentText(), self.treatment_combo.currentText(), parameters

    def _validate(self) -> None:
        date_column, treatment_column, parameters = self.selected_columns()
        if date_column == treatment_column:
            QMessageBox.warning(self, "列选择错误", "日期列和处理方式列不能相同。")
            return
        if not parameters:
            QMessageBox.warning(self, "列选择错误", "请至少选择一个植株参数列。")
            return
        self.accept()
