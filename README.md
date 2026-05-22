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

使用 PyInstaller：

```powershell
pyinstaller --noconsole --name AgriParameterAnalyzer main.py
```

或使用 Nuitka：

```powershell
python -m nuitka --standalone --windows-console-mode=disable --enable-plugin=pyside6 main.py
```

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
