# 变更说明

本文件记录项目按阶段推进的主要功能进展、验证结果和已知限制。

## [Unreleased] - 2026-05-25

### 变更

- 模块二统计表新增 `sum`、`sum_diff_vs_control`、`sum_diff_percent_vs_control` 列，用于查看总产量等累积型参数的总和差异与相对对照差异百分比。
- debug 日志改为每次启动生成带时间戳的 `debug_YYYYMMDD_HHMMSS.log`，并默认仅保留最近 10 份启动日志，避免单个日志文件长期累积过大。
- 模块三显著性结果新增可信度解释字段：Welch t-test 输出均值差、Welch_df、CI95%、Hedges' g、效应量解释、样本量判断、可信度判断和中文结果建议。
- 模块三多组分析新增解释增强：one-way ANOVA 输出 eta_squared、整体效应量解释、整体可信度和结果建议；Tukey HSD 两两比较输出 CI95%、Hedges' g、效应量解释、样本量判断、可信度判断和结果建议。

### 验证

- `python -m compileall main.py src tests`：通过。
- `python -m pytest`：34 passed。
- 使用 `C:\Users\jinji\Desktop\20250524-产量.xlsx`、`C:\Users\jinji\Desktop\20250524-单果重.xlsx`、`C:\Users\jinji\Desktop\20250524-尾果重.xlsx` 完成真实数据格式化和模块二统计冒烟测试。
- 本次模块三可信度解释更新后，`python -m compileall main.py src tests`：通过。
- 本次模块三可信度解释更新后，`python -m pytest`：34 passed。

## [0.1.0] - 2026-05-21

### 新增

- 搭建 Python + PySide6 桌面应用项目骨架。
- 完成模块一“参数格式化”：
  - 支持导入 `.xlsx`、`.xls`、`.csv`。
  - 支持智能识别日期列、处理方式列和数值型植株参数列。
  - 支持弹窗确认列识别结果并选择保留参数列。
  - 自动计算 `isoweek`。
  - 输出固定列顺序：`序号 | 日期 | isoweek | 处理方式 | [参数列...]`。
  - 支持 QTableView 预览、复制和导出 `.xlsx`。
- 预留模块二“数据情况输出”和模块三“显著水平判断”标签页入口。
- 新增示例数据目录 `example_data_sources/`，用于同步真实或脱敏示例数据源。
- 新增项目记忆文件 `agents.md`。
- 新增基础测试文件，覆盖模块一核心格式化逻辑。

### 变更

- 放宽依赖版本上限，兼容 Python 3.14。
- README 增加慢速网络下依赖安装超时建议。
- `.gitignore` 明确忽略输出目录和用户私有数据，同时放行 `example_data_sources/`。

### 验证

- `python -m compileall main.py src tests`：通过。
- `python -m pytest`：5 passed。
- 完整依赖已在 Python 3.14.5 环境安装验证。

### 已知限制

- 模块二、模块三目前仍为占位入口，尚未实现统计、绘图和导出流程。
- GUI 已完成代码层面实现，仍建议后续结合真实示例数据进行人工点击验收。
- 对照组命名、显著性标记方式、误差线类型等细节等待真实数据和偏好确认。

## [0.2.0] - 2026-05-21

### 新增

- 实现模块二“数据情况输出”第一版，复用模块一格式化后的 DataFrame。
- 新增按处理方式汇总 `n / mean / SD / SEM / min / max` 的描述统计。
- 支持自动识别 `对照`、`CK`、`Control` 为对照组，并计算相对对照差异与差异百分比。
- 新增模块二统计表预览、统计表 `.xlsx` 导出和科研风格灰度图表导出。
- 新增模块二核心逻辑与样例数据流程测试。
- 新增 `example_data_sources/TestDataSource.xlsx` 作为模块二描述统计与图表流程的真实样例数据源。
- 在 `agents.md` 追加项目 AI 协作规范，明确 CHANGELOG 维护规则与中文 Git 提交信息格式。
- 修正模块一对 `采收日` 等日期列的自动识别，并支持 Excel 序列日期解析，避免将纯数字序号误判为日期列。
- 使用 `TestDataSource.xlsx` 跑通模块一格式化与模块二统计输出，生成格式化表、统计表和单果重图表。

### 验证

- `python -m compileall main.py src tests`：通过。
- `python -m pytest`：12 passed。
- `QT_QPA_PLATFORM=offscreen` 下实例化主窗口：通过，模块二加载为 `SummaryTab`。

## [0.2.1] - 2026-05-22

### 变更

- 模块二统计表预览与导出统一按三位有效数字四舍五入，`n` 与 `序号` 等 ID/计数字段保持整数。
- 模块二新增组内 IQR 1.5 倍离群值识别，统计和图表默认剔除离群值，并在导出 Excel 的 `outliers` sheet 记录离群数据 ID、原始值、上下限与判定规则。
- 模块二图表柱体宽度调整为 0.4，y 轴根据 `mean ± error` 自动设置上下限并保留约 20% 富余。
- 模块二两组柱状图改为 x 轴左边界、两组柱中心和右边界等距分布，并在误差线上方标注 `mean ± error`。
- 模块一格式化结果中的 `序号` 优先沿用原始数据源中的序号/编号/id 列，用于后续异常值定位。
- 使用 `TestDataSource.xlsx` 重新生成模块二输出，识别单果重离群值 4 个，剔除后处理组 `n=72`、对照组 `n=77`。

### 验证

- `python -m compileall main.py src tests`：通过。
- `python -m pytest`：18 passed。

## [0.2.2] - 2026-05-22

### 新增

- 新增 `docs/chart-style-guide.md`，沉淀模块二图表样式、误差线、y 轴范围、离群值处理口径与模块三显著性图表扩展规范。

## [0.3.0] - 2026-05-22

### 新增

- 实现模块三“显著水平判断”，复用模块一格式化结果和模块二离群值剔除口径。
- 两组数据默认使用 Welch t-test，并在显著性图表中添加星号标注。
- 多组数据默认使用 one-way ANOVA + Tukey HSD，并在显著性图表中添加字母分组。
- 新增模块三显著性结果表预览、`.xlsx` 导出和科研风格图表导出。
- 模块三图表遵循 `docs/chart-style-guide.md`：灰度柱状图、4:3、300 dpi、柱宽 0.4、默认 SEM、三位有效数字。
- 新增模块三核心逻辑、GUI 流程和真实样例数据贯通测试。

### 变更

- 模块一完成参数格式化后，同时解锁模块二和模块三。
- README 更新模块二、模块三当前功能状态。

### 验证

- `python -m compileall main.py src tests`：通过。
- `python -m pytest`：26 passed。

## [0.3.1] - 2026-05-22

### 变更

- 模块二导出图表从处理组柱状图调整为基于 `isoweek` 的散点-均值折线趋势图，用于展示数据分布和时间变化。
- 模块二趋势图按处理方式绘制原始散点，并按 `处理方式 + isoweek` 均值点连接趋势线；同一周内不同处理不做横向错位。
- 模块二趋势图原始散点按处理方式在 x 轴方向轻微错开，避免同周不同处理点完全重叠；均值点和趋势线仍保持在原始 `isoweek` 坐标。
- 模块二趋势图新增极小确定性 y jitter，用于增强同周堆叠点的富集可见性，均值线仍使用真实数值。
- 模块二新增处理分布散点图，以 `处理方式` 为 x 轴展示全周期数据分布，并用横向 jitter 与点大小/透明度表达局部富集。
- 模块二界面拆分为“导出日期趋势图”和“导出处理分布图”两个图表出口。
- 模块三继续保留柱状图、误差线和显著性星号/字母分组，避免模块二趋势图改造影响显著性图。
- 更新 `docs/chart-style-guide.md`，明确模块二使用日期趋势散点图、模块三使用显著性柱状图。

### 验证

- `python -m compileall main.py src tests`：通过。
- `python -m pytest`：28 passed。
- 使用 `TestDataSource.xlsx` 重新生成模块二趋势图，x 轴为 `isoweek`，输出包含处理组和对照组均值趋势线。

## [0.3.2] - 2026-05-23

### 变更

- 模块二处理分布图新增每个处理组右侧的竖向分箱密度条，按组内参数值分箱并用灰度深浅表达富集程度。
- 密度条最密集区间新增短横线与 `密集区 {value}` 标注，数值沿用三位有效数字格式。
- 处理分布图继续使用剔除离群值后的数据；密度条仅作为视觉辅助，不改变统计表、离群值报告或模块三显著性分析。
- 更新 `docs/chart-style-guide.md`，补充分箱密度条的布局、归一化和标注规则。

### 验证

- `python -m compileall main.py src tests`：通过。
- `python -m pytest`：31 passed。

## [0.3.3] - 2026-05-23

### 变更

- 更新 `agents.md` 项目记忆，记录模块一、模块二、模块三当前完成状态与真实数据验证阶段。
- 明确数据观察趋势图以 `isoweek` 为 x 轴，周为最小汇总周期，不按原始日期绘制趋势图。
- 清理模块二残留误差线 UI 控件，误差线设置保留在模块三显著性图表中。
- 模块二周趋势图、处理分布图和模块三显著性柱状图新增右下角注记：`默认剔除离群值（IQR 1.5×）`。
- 在项目记忆中将共享应用状态 / 数据上下文列为后续高优先级结构优化。

### 验证

- `python -m compileall main.py src tests`：通过。
- `python -m pytest`：33 passed。

## [0.4.0-beta.1] - 2026-05-24

### 新增

- 新增 `scripts/build_windows.ps1`，用于清理本地构建产物、运行编译检查和测试，并生成 PyInstaller 目录版内部测试程序。
- 新增 `docs/packaging-windows.md`，记录 Windows 内部测试版打包入口、分发方式、冒烟测试流程和常见问题。

### 变更

- 应用版本号更新为 `0.4.0-beta.1`。
- README 打包说明调整为优先使用 PyInstaller 目录版，并指向内部测试版打包文档。

### 验证

- `.\scripts\build_windows.ps1`：通过。
- `python -m compileall main.py src tests`：通过。
- `python -m pytest`：33 passed。
- 已生成 `dist\AgriParameterAnalyzer\AgriParameterAnalyzer.exe`。
- 打包后 exe 启动冒烟测试通过，进程可正常启动并保持运行。

## [0.4.0-beta.2] - 2026-05-24

### 新增

- 新增 debug 日志配置，源码运行写入 `outputs\debug.log`，打包后 exe 运行写入 `dist\AgriParameterAnalyzer\logs\debug.log`。
- 模块一导入、列识别、确认列弹窗、弹窗校验、格式化计算和表格刷新流程新增关键日志，用于定位内部测试版卡顿位置。

### 变更

- 应用版本号更新为 `0.4.0-beta.2`。
- README 和 Windows 打包说明补充 debug 日志位置与排查建议。

### 验证

- `python -m compileall main.py src tests`：通过。
- `python -m pytest`：33 passed。
- `.\scripts\build_windows.ps1`：通过。
- 打包后 exe 启动冒烟测试通过，并确认生成 `dist\AgriParameterAnalyzer\logs\debug.log`。

## [0.4.0-beta.4] - 2026-05-24

### 修复

- 修复内部测试版在检查确认列弹窗返回值后崩溃的问题：避免使用 PySide 弹窗实例上的 enum 属性比较，改为稳定的整数返回码判断。
- 为“确认列并格式化”槽函数增加兜底异常日志，未预期错误会写入 `debug.log` 并弹出错误提示。

### 变更

- 应用版本号更新为 `0.4.0-beta.4`。
- Windows 打包脚本新增真实数据预检：若存在 `Desktop\20250524-单果重.xlsx`，打包前先执行读取、列识别和格式化核心流程。
- 新增 `scripts/smoke_formatting_data.py`，用于稳定执行真实数据格式化预检。
- Windows 打包脚本显式检查编译、测试、真实数据预检和 PyInstaller 的退出码，任一步失败都会停止打包。

### 验证

- `python -m compileall main.py src tests`：通过。
- `python -m pytest`：33 passed。
- `python scripts\smoke_formatting_data.py --default-desktop`：通过，使用 `C:\Users\jinji\Desktop\20250524-单果重.xlsx` 生成 177 行格式化结果。
- `.\scripts\build_windows.ps1`：通过，打包前真实数据预检通过。
- 打包后 exe 启动冒烟测试通过，并确认生成 `dist\AgriParameterAnalyzer\logs\debug.log`。

## [0.4.0-beta.3] - 2026-05-24

### 修复

- 修复内部测试版在“确认列并格式化”弹窗关闭后可能卡住的问题：列选择结果改为在弹窗校验通过时缓存为普通 Python 值，弹窗关闭后不再重新读取 Qt 控件状态。

### 变更

- 应用版本号更新为 `0.4.0-beta.3`。
- “确认列并格式化”流程增加弹窗返回值检查和读取缓存选择前的细粒度日志。

### 验证

- `python -m compileall main.py src tests`：通过。
- `python -m pytest`：33 passed。
- `.\scripts\build_windows.ps1`：通过。
- 打包后 exe 启动冒烟测试通过，并确认生成 `dist\AgriParameterAnalyzer\logs\debug.log`。
