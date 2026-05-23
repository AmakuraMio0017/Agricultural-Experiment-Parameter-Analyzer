# 项目记忆

## 项目概况

- 项目名称：Agricultural Experiment Parameter Analyzer
- 目标：构建 Python + PySide6 桌面应用，用于园艺/农业科研数据处理。
- 当前阶段：已完成项目骨架、GitHub 同步、模块一“参数格式化”、模块二“数据情况输出”和模块三“显著水平判断”基础功能；仍处于真实数据验证与细节调试阶段。
- 远程仓库：https://github.com/AmakuraMio0017/Agricultural-Experiment-Parameter-Analyzer.git

## 当前技术约定

- Python：3.10+，当前本地验证环境为 Python 3.14.5。
- GUI：PySide6。
- 数据处理：pandas、numpy。
- 绘图：matplotlib，科研风格，灰度优先，4:3，dpi >= 300。
- 统计：scipy.stats。
- 打包：PyInstaller 或 Nuitka。
- 单入口：`main.py`。

## 已完成内容

- 根目录已包含 README、requirements、.gitignore、tests、data、outputs、src。
- 模块一支持：
  - 导入 `.xlsx`、`.xls`、`.csv`
  - 自动识别日期列、处理方式列、数值参数列
  - 弹窗确认列选择
  - 计算 `isoweek`
  - 固定表头输出：`序号 | 日期 | isoweek | 处理方式 | [参数列...]`
  - QTableView 预览、复制、导出 `.xlsx`
- 模块二支持：
  - 复用模块一格式化后的 DataFrame
  - 按处理方式输出 `n / mean / SD / SEM / min / max`
  - 自动识别 `对照`、`CK`、`Control` 为对照组，并计算相对对照差异
  - 组内 IQR 1.5 倍离群值识别与 outliers sheet 导出
  - 周趋势散点-均值折线图
  - 处理分布图
- 模块三支持：
  - 复用模块一格式化后的 DataFrame 和模块二离群值剔除口径
  - 两组 Welch t-test 与星号标注
  - 多组 one-way ANOVA + Tukey HSD 与字母分组
  - SEM/SD 误差线柱状图
  - 显著性结果、统计摘要和离群值报告导出

## 数据目录约定

- `data/`：应用自带示例或模板。
- `example_data_sources/`：后续用户提供的真实或脱敏示例数据源，会随 GitHub 同步。
- `outputs/`：应用输出目录，默认不纳入 Git；只保留 `.gitkeep`。

## 后续实现偏好

- 模块二、模块三应优先复用模块一格式化后的 DataFrame。
- 高优先级结构优化：后续新增共享应用状态或数据上下文，例如 `AppState` / `DataContext`，集中保存 `formatted_df`、数据来源、离群值规则和图表口径，避免各模块分散保存状态。
- 对照组识别优先支持：`对照`、`CK`、`Control`。
- 数据观察趋势图默认以 `isoweek` 为 x 轴，周是最小汇总周期；不按原始日期作为 x 轴绘制趋势图。
- 模块二负责描述统计、离群值报告、周趋势散点-均值折线图和处理分布图；模块二不再提供误差线 UI。
- 模块三负责显著性判断、SEM/SD 误差线柱状图、星号标注和 Tukey 字母分组。
- 离群值默认按组内 IQR 1.5 倍剔除；当前版本不提供用户选择“是否剔除离群值”的开关。
- 所有默认剔除离群值的图表应在右下角注明：`默认剔除离群值（IQR 1.5×）`。
- 显著性绘图默认：
  - 两组比较用星号标注。
  - 多组比较建议用 Tukey HSD 结果生成字母分组。
- 模块三误差线默认建议 SEM；如用户确认使用 SD，则以用户偏好为准。

## 验证记录

- `python -m compileall main.py src tests`：已通过。
- `python -m pytest`：当前最新记录为 29 passed。
- 依赖安装在非中国 IP 链路约 1 MB/s 时建议超时 15-20 分钟。

# 项目 AI 协作规范

## 文档维护规则
- 每次代码修改后，自动更新 CHANGELOG.md 记录变更
- 不要修改 CHANGELOG.md 中已经存在的旧记录，只追加新内容
- 在 CHANGELOG.md 中标注日期和变更摘要

## Git 操作规则
- 用户提出保存所有工作并结束本地操作后提醒我提交代码变更到git并同步推送至GitHub
- 提交信息使用中文，格式：类型: 简述
