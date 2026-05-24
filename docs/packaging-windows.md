# Windows 内部测试版打包说明

本项目首个内部测试版使用 PyInstaller 目录版打包。目录版会生成一个完整文件夹，运行其中的 `.exe` 即可启动应用；相比单文件版，它更容易排查缺少依赖、Qt 插件、matplotlib 后端或 Excel 读写相关问题。

## 打包方式

在项目根目录执行：

```powershell
.\scripts\build_windows.ps1
```

脚本会依次完成：

- 清理本地 `build/`、`dist/` 和旧的 `AgriParameterAnalyzer.spec`。
- 运行 `python -m compileall main.py src tests`。
- 运行 `python -m pytest`。
- 如果存在 `Desktop\20250524-单果重.xlsx`，通过 `scripts\smoke_formatting_data.py --default-desktop` 使用该真实数据执行读取、列识别和格式化预检。
- 使用 PyInstaller 生成目录版程序。

成功后入口文件为：

```text
dist\AgriParameterAnalyzer\AgriParameterAnalyzer.exe
```

打包后的 debug 日志位置为：

```text
dist\AgriParameterAnalyzer\logs\debug.log
```

如果内部测试时出现导入文件后卡顿，先查看该日志。日志会记录文件读取、自动列识别、确认列弹窗、格式化计算和表格刷新等关键步骤。

内部测试分发时，请复制整个目录：

```text
dist\AgriParameterAnalyzer\
```

不要只复制单独的 `.exe` 文件。`dist/`、`build/` 和 `.spec` 文件属于本地打包产物，默认不提交到 Git。

## 当前测试目标

首轮内部测试以当前 Windows 设备为主，确认三模块 GUI 能通过 exe 稳定启动、导入数据、导出 Excel 和图表。后续如果需要在无 Python 的干净 Windows 机器上测试，应直接复制整个 `dist\AgriParameterAnalyzer\` 目录进行验证。

建议的冒烟测试：

- 运行 `AgriParameterAnalyzer.exe`，确认不弹出控制台窗口。
- 使用 `data\sample_parameters.csv` 完成模块一导入、列确认、格式化和 `.xlsx` 导出。
- 使用 `example_data_sources\TestDataSource.xlsx` 跑通模块一、模块二和模块三。
- 验证模块二可导出统计表、离群值报告、日期趋势图和处理分布图。
- 验证模块三可导出显著性结果和显著性图表。
- 将 `dist\AgriParameterAnalyzer\` 复制到另一个本地路径后再次启动。

## 常见问题

- 杀毒软件提示风险：PyInstaller 打包程序偶尔会触发误报。内部测试时优先确认来源和构建机器可信，不建议关闭系统防护作为常规流程。
- 首次启动较慢：目录版通常比单文件版快，但 Qt、pandas、matplotlib 等依赖较大，首次启动仍可能需要几秒。
- 缺少 DLL 或 Qt 插件：优先重新运行 `.\scripts\build_windows.ps1`，并确认分发时复制的是整个 `dist\AgriParameterAnalyzer\` 目录。
- matplotlib 图表异常：确认 exe 中的图表导出流程能保存 `.png`，并优先在当前设备复现具体参数和输入文件。
- Excel 读写失败：`.xlsx` 依赖 `openpyxl`，`.xls` 读取依赖 `xlrd`。先用源码环境复现，再重新打包验证。
- Python 3.14 兼容问题：当前可先使用本机 Python 3.14 环境打包；若 PyInstaller 或科学计算依赖出现兼容性问题，再切换到 Python 3.12/3.13 的独立构建虚拟环境。
