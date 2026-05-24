# 农业科研数据处理桌面应用

基于 Python + PySide6 的园艺/农业科研数据处理工具。当前阶段已完成项目骨架、模块一“参数格式化”、模块二“数据情况输出”和模块三“显著水平判断”。

## 功能状态

- 模块一：导入 Excel/CSV，智能识别日期列、处理方式列和植株参数列，计算 ISO week，按固定表头格式预览并导出 `.xlsx`。
- 模块二：按处理方式输出 `n / mean / SD / SEM / min / max`、相对对照差异、离群值报告和科研风格图表。
- 模块三：复用模块二清洗口径，支持两组 Welch t-test、多组 ANOVA + Tukey HSD、显著性结果导出和带星号/字母分组的柱状图导出。

## 环境配置

建议使用 Python 3.10 或更高版本。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

如果访问非中国大陆源下载速度约为 1 MB/s，完整依赖包体较大，尤其是 PySide6 相关 wheel。建议将自动化安装命令超时时间设置为至少 15 分钟，网络波动明显时使用 20 分钟或更长。

## 运行应用

```powershell
python main.py
```

可使用 `data/sample_parameters.csv` 进行模块一导入测试。

## 打包应用

首个内部测试版推荐使用 PyInstaller 目录版。它会生成完整程序文件夹，便于排查依赖和 Qt 插件问题：

```powershell
.\scripts\build_windows.ps1
```

成功后运行入口为：

```text
dist\AgriParameterAnalyzer\AgriParameterAnalyzer.exe
```

内部测试分发时请复制整个 `dist\AgriParameterAnalyzer\` 文件夹，不要只复制单独的 `.exe` 文件。详细说明见 `docs/packaging-windows.md`。

## Debug 日志

源码运行时，debug 日志写入：

```text
outputs\debug.log
```

打包后的 exe 运行时，debug 日志写入：

```text
dist\AgriParameterAnalyzer\logs\debug.log
```

如果导入文件或“确认列并格式化”环节出现卡顿，请优先查看该日志，确认流程停在文件读取、列识别、确认弹窗、格式化计算还是表格刷新。

## Git 与远程同步

首次创建 GitHub 同名仓库后，在本地执行：

```powershell
git remote add origin <仓库地址>
git branch -M main
git push -u origin main
```

## 提交信息规范

建议使用语义化提交：

- `feat: 完成参数格式化模块`
- `fix: 修复日期列识别异常`
- `docs: 更新运行说明`
- `test: 添加格式化逻辑测试`
- `refactor: 拆分统计计算模块`

## 贡献指南

1. 从 `main` 分支创建功能分支，例如 `feat/module-two-plots`。
2. 提交前运行测试：`pytest`。
3. Pull Request 中说明变更内容、测试结果和可能影响。
4. 用户输入数据、格式化结果和图表输出不纳入 Git 版本控制；项目自带示例文件可保留。
