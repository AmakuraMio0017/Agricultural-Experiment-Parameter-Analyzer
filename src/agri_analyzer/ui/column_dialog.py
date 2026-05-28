from __future__ import annotations

import logging

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


logger = logging.getLogger(__name__)


class ColumnConfirmDialog(QDialog):
    def __init__(self, columns: list[str], detection: ColumnDetection, parent=None) -> None:
        super().__init__(parent)
        self._selected_columns: tuple[str, str, str | None, list[str]] | None = None
        logger.debug(
            "Creating column confirmation dialog; columns=%s; detected_date=%r; detected_treatment=%r; detected_parameters=%s",
            columns,
            detection.date_column,
            detection.treatment_column,
            detection.parameter_columns,
        )
        self.setWindowTitle("确认列识别结果")
        self.resize(520, 420)

        self.date_combo = QComboBox()
        self.date_combo.addItems(columns)
        self.treatment_combo = QComboBox()
        self.treatment_combo.addItems(columns)
        self.replicate_combo = QComboBox()
        self.replicate_combo.addItem("无")
        self.replicate_combo.addItems(columns)

        if detection.date_column in columns:
            self.date_combo.setCurrentText(detection.date_column)
        if detection.treatment_column in columns:
            self.treatment_combo.setCurrentText(detection.treatment_column)
        if detection.replicate_column in columns:
            self.replicate_combo.setCurrentText(detection.replicate_column)

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
        form.addRow("小区/重复列", self.replicate_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(message))
        layout.addLayout(form)
        layout.addWidget(scroll)
        layout.addWidget(buttons)

    def selected_columns(self) -> tuple[str, str, str | None, list[str]]:
        if self._selected_columns is not None:
            return self._selected_columns
        parameters = [check.text() for check in self.parameter_checks if check.isChecked()]
        replicate_column = self.replicate_combo.currentText()
        if replicate_column == "无":
            replicate_column = None
        return self.date_combo.currentText(), self.treatment_combo.currentText(), replicate_column, parameters

    def _validate(self) -> None:
        parameters = [check.text() for check in self.parameter_checks if check.isChecked()]
        date_column = self.date_combo.currentText()
        treatment_column = self.treatment_combo.currentText()
        replicate_column = self.replicate_combo.currentText()
        logger.debug(
            "Validating column dialog selection; date=%r; treatment=%r; parameters=%s",
            date_column,
            treatment_column,
            parameters,
        )
        if date_column == treatment_column:
            logger.warning("Column dialog validation failed: date and treatment columns are identical.")
            QMessageBox.warning(self, "列选择错误", "日期列和处理方式列不能相同。")
            return
        selected_identity_columns = {date_column, treatment_column}
        if replicate_column != "无":
            if replicate_column in selected_identity_columns:
                QMessageBox.warning(self, "列选择错误", "小区/重复列不能和日期列或处理方式列相同。")
                return
            if replicate_column in parameters:
                QMessageBox.warning(self, "列选择错误", "小区/重复列不能同时作为数值参数列。")
                return
        if not parameters:
            logger.warning("Column dialog validation failed: no parameter columns selected.")
            QMessageBox.warning(self, "列选择错误", "请至少选择一个植株参数列。")
            return
        self._selected_columns = (
            date_column,
            treatment_column,
            None if replicate_column == "无" else replicate_column,
            parameters,
        )
        logger.debug("Column dialog validation passed; accepting dialog.")
        self.accept()
