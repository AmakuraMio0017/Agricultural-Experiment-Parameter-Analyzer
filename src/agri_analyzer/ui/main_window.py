from __future__ import annotations

import pandas as pd
from PySide6.QtWidgets import QMainWindow, QTabWidget

from src.agri_analyzer import __app_name__
from src.agri_analyzer.ui.formatting_tab import FormattingTab
from src.agri_analyzer.ui.significance_tab import SignificanceTab
from src.agri_analyzer.ui.summary_tab import SummaryTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(__app_name__)
        self.resize(1100, 720)
        self.formatted_df: pd.DataFrame | None = None

        self.tabs = QTabWidget()
        self.formatting_tab = FormattingTab()
        self.module_two_tab = SummaryTab()
        self.module_three_tab = SignificanceTab()

        self.tabs.addTab(self.formatting_tab, "模块一：参数格式化")
        self.tabs.addTab(self.module_two_tab, "模块二：数据情况输出")
        self.tabs.addTab(self.module_three_tab, "模块三：显著水平判断")
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)

        self.formatting_tab.formatting_completed.connect(self.unlock_analysis_modules)
        self.setCentralWidget(self.tabs)

    def unlock_analysis_modules(self, dataframe: pd.DataFrame) -> None:
        self.formatted_df = dataframe.copy()
        self.module_two_tab.set_formatted_data(self.formatted_df)
        self.module_three_tab.set_formatted_data(self.formatted_df)
        self.tabs.setTabEnabled(1, True)
        self.tabs.setTabEnabled(2, True)
