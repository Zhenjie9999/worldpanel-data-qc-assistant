# Worldpanel Data QC Assistant - 产品设计与开发计划

日期：2026-05-27

## 1. 产品定义

Worldpanel Data QC Assistant 是一个面向 Worldpanel 分析与交付团队的数据质检产品。第一版聚焦两个高价值场景：

1. Data Output QC：检查从 Powerview 导出的 Excel 数据产出。
2. Delivery QC：检查客户交付前的 PPT 和/或 Excel 文件。

产品支持单 Excel、单 PPT、多 Excel、以及 PPT + Excel 混合上传。系统会自动识别用户上传的文件组合，选择对应的质检流程，并生成 QC Report，帮助用户在分析或交付前发现问题、修正问题，并保留质检记录。

这个产品不替代 Powerview、Excel 或 PowerPoint，而是在现有工作流之上增加一层质量控制：

```text
Powerview -> Excel 数据产出 / 工作文件 -> PPT 交付文件 -> QC Report
```

## 2. 目标用户

核心用户：

- 从 Powerview 导出数据并制作 Excel 工作文件的分析师。
- 在客户交付前 review PPT 的项目经理。
- 需要统一数据质检标准的交付团队。

扩展用户：

- 希望了解团队高频错误类型的团队负责人。
- 维护通用质检规则和阈值的管理员。

## 3. 核心使用场景

### 3.1 Data Output QC

用户上传一个或多个从 Powerview 导出的 Excel 文件，或项目分析中使用的 Excel 工作文件。

这个场景要回答的问题是：

```text
这个 Excel 数据产出本身是否可靠，可以继续用于分析或交付？
```

重点检查内容：

- 空值、错误值、异常 0、空白数据块。
- Total、Subtotal 与分项加总是否一致。
- Share、Contribution、百分比、同比/环比变化等计算是否合理。
- Sales value、Volume、Price、Penetration、Frequency、Buyers、Occasions、Spend per buyer 等核心 KPI 之间的基础逻辑关系。
- 单位、百分号、小数位、正负号、四舍五入是否一致。
- 隐藏行列、公式被手动覆盖、同一列公式不一致等风险。
- 文件层面的风险，例如 period、scope、项目名称是否清楚。

### 3.2 Delivery QC

用户上传一个 PPT，或一个 PPT 加一个或多个 Excel 文件。

这个场景要回答的问题是：

```text
这个 PPT 或 PPT + Excel 组合是否可以放心发给客户？
```

重点检查内容：

- PPT 中数字格式是否统一。
- 同一个 KPI 在不同页面是否一致。
- Source、Base、Period、Footnote 是否缺失。
- 页面标题或结论是否与数据方向存在潜在冲突。
- 同一数字或同一指标在不同页面是否出现不一致。
- 在 PPT + Excel 模式下，PPT 中的数字是否能追溯到 Excel。
- 在 PPT + Excel 模式下，PPT 是否存在未同步、四舍五入错误、单位转换错误或版本不一致问题。

## 4. 文件组合识别逻辑

产品不应要求用户手动选择复杂模式。用户只需要拖入文件，系统自动识别文件类型和组合，并决定执行哪些检查。

| 上传文件 | 自动执行的检查 |
| --- | --- |
| 单个 Excel | Data Output QC |
| 多个 Excel | Data Output QC + Excel 之间一致性检查 |
| 单个 PPT | Delivery QC 中的 PPT-only 检查 |
| PPT + 一个或多个 Excel | Delivery QC + Cross-file QC |

上传后，系统应在开始检查前展示一个简短确认，例如：

```text
你上传了：
- 1 个 PPT
- 3 个 Excel

系统将执行：
- PPT Delivery QC
- Excel Data Output QC
- PPT-Excel Cross-file QC
```

## 5. MVP 范围

第一版 MVP 应包含：

- 支持上传 `.xlsx` 和 `.pptx` 文件。
- 自动识别文件类型和文件组合。
- 自动选择对应的 QC 工作流。
- 从 Excel 和 PPT 中提取可见数字、百分比、单位和周边文本。
- 执行 Excel-only QC 规则。
- 执行 PPT-only QC 规则。
- 执行 PPT + Excel 的跨文件数字匹配。
- 支持中文和英文混合文本。
- 生成页面版 QC Report。
- 支持导出 Excel 或 PDF 格式的 QC Report。
- 将问题分为 High、Medium、Low 三个严重程度。
- 提供业务用户能理解的问题解释和建议动作。

第一版 MVP 暂不包含：

- 直接连接 Powerview。
- Office 插件。
- 自动修改 PPT。
- 对所有业务结论做完整 AI 判断。
- 保证所有图表标签或手动编辑数字都能 100% 追溯来源。
- 复杂的项目级规则配置界面。

## 6. QC Report 设计

QC Report 必须让非技术用户也能看懂。

建议包含以下部分：

1. Summary 总览
2. High-risk issues 高风险问题
3. Excel QC issues
4. PPT QC issues
5. Cross-file QC issues
6. Unverified numbers 无法验证来源的数字
7. Export and audit information 导出与留档信息

每个问题建议包含：

| 字段 | 说明 |
| --- | --- |
| Severity | High、Medium、Low |
| File | 文件名 |
| Location | Excel sheet/cell 或 PPT 页码/文本框 |
| Issue type | 计算、格式、缺失 source、数据不一致等 |
| Description | 用业务语言解释问题 |
| Evidence | 抽取到的数值或对比结果 |
| Suggested action | 建议用户如何检查或修正 |

示例：

```text
严重程度：High
位置：PPT 第 12 页
问题：PPT 数字与 Excel 不一致
证据：PPT 显示 6.1%，Excel 候选值为 6.0%
可能原因：PPT 在 Excel 更新后没有同步
建议动作：确认是否应以当前 Excel 数值替换 PPT 数字
```

## 7. 规则模型

规则建议分为三层。

### 7.1 通用规则

适用于所有 Excel 和 PPT 的规则：

- 数据区域中存在空值。
- 出现 `#DIV/0!`、`#N/A`、`#VALUE!` 等错误值。
- 小数位不一致。
- 百分号使用不一致。
- 可疑的 0 值。
- Total 和 Subtotal 不一致。
- PPT 中缺失 source、base、period 或 footnote。

### 7.2 Worldpanel 业务规则

基于 Worldpanel 常见指标和交付内容的规则：

- Sales value、Volume、Price、Buyer、Household、Penetration、Frequency、Occasions、Spend 等指标之间的关系检查。
- Contribution 和 Share 的合理性检查。
- 正负方向一致性检查。
- Period 和 Scope 一致性检查。
- 在结构可识别的情况下，检查 category、channel、region、demographic split 等维度是否一致。

### 7.3 项目规则

后续可针对特定客户、报告或模板增加项目规则：

- 客户特定 KPI 命名。
- 模板特定必填脚注。
- 项目特定四舍五入规则。
- 重复交付项目的标准页面结构。

MVP 阶段，项目规则可以先通过简单配置文件或手动规则管理，不建议第一版就做复杂的规则管理界面。

## 8. 跨文件匹配逻辑

Cross-file QC 的核心是将 PPT 中出现的数字，与 Excel 中可能的来源建立匹配关系。

匹配时应考虑：

- 标准化后的数字值。
- 百分比和小数等价关系，例如 `6%` 与 `0.06`。
- 四舍五入容忍，例如 `6.0469%` 可以匹配 PPT 中的 `6.0%`。
- 明显单位转换，例如 million 和 raw value。
- 数字周边的 label、KPI 名称、品牌、品类、period、页面语境。
- 多个候选来源。

系统不能把不确定的匹配强行认定为准确来源。建议使用匹配置信度：

| 置信度 | 含义 |
| --- | --- |
| High | 数值和语境都高度匹配 |
| Medium | 数值匹配，但语境较弱 |
| Low | 只能认为是可能匹配 |
| None | 没有找到合理 Excel 来源 |

高风险跨文件问题包括：

- PPT 数字找不到合理 Excel 来源。
- PPT 数字与最可能的 Excel 来源不一致。
- 同一个 PPT KPI 在不同页面出现不同数值。
- Excel 文件看起来已更新，但 PPT 仍保留旧数字。

## 9. 系统架构

MVP 推荐架构：

```text
Upload UI
  -> File Type Detector
  -> Excel Parser
  -> PPT Parser
  -> Number Normalizer
  -> Rule Engine
  -> Cross-file Matcher
  -> QC Report Generator
  -> Export Module
```

模块职责：

| 模块 | 职责 |
| --- | --- |
| Upload UI | 上传 Excel/PPT 文件，并展示系统识别出的 QC 模式 |
| File Type Detector | 识别文件类型和文件组合 |
| Excel Parser | 提取 sheet、单元格、公式、数值、格式、隐藏区域和表格结构 |
| PPT Parser | 提取 slide 文本、表格文本、可识别图表标签和周边语境 |
| Number Normalizer | 标准化数字、百分比、符号、单位和四舍五入结果 |
| Rule Engine | 执行 QC 规则并分配严重程度 |
| Cross-file Matcher | 将 PPT 数字与 Excel 候选来源匹配 |
| QC Report Generator | 生成结构化问题清单和总览指标 |
| Export Module | 导出 QC Report，用于分享和留档 |

## 10. 技术建议

第一版建议优先做上传式 Web 工具或桌面工具，而不是 Office 插件。

推荐技术路线：

- 前端：简单 Web App，用于上传、进度展示、报告查看和导出。
- 后端：Python 或 Node.js 服务。
- Excel 解析：`openpyxl` 处理 `.xlsx`，必要时补充 Open XML 解析。
- PPT 解析：`python-pptx`，必要时补充 Open XML 解析文本、表格和 shape 信息。
- 规则引擎：使用 JSON/YAML 定义规则，由 Python 执行。
- 存储：临时本地存储或内网服务器临时存储。
- 部署：公司内网服务器；如果文件安全要求更高，可考虑打包成本地桌面版。

安全要求：

- 上传文件应只做临时保存。
- 用户需要清楚文件是在本地处理，还是上传到公司内网服务器处理。
- MVP 阶段不应把客户名称、敏感数据或完整报告内容发送到外部 API。
- 除非有审计要求，否则 QC 日志不应保存完整文件内容。

## 11. 开发计划

### Phase 0：规则和样例定义，1 周

目标：

- 收集 10-20 组代表性的 Excel/PPT 样例。
- 定义 Top 30 高频 QC 规则。
- 确认四舍五入和容忍标准。
- 定义 QC Report 结构。
- 确认 MVP 成功标准。

产出：

- 样例文件清单。
- 规则清单 v1。
- QC Report 模板。
- MVP 验收标准。

### Phase 1：文件解析原型，1-2 周

目标：

- 提取 Excel 的 sheet 名称、单元格、数值、公式和格式。
- 提取 PPT 的页面文本、表格、数字和周边 label。
- 标准化数字、百分比、单位和符号。

产出：

- Excel extraction JSON。
- PPT extraction JSON。
- Number normalization module。
- 基于真实样例的解析准确率评估。

验收标准：

- 能从代表性 Excel/PPT 文件中提取至少 90% 的可见业务数字。

### Phase 2：Excel-only Data Output QC，2 周

目标：

- 实现核心 Excel QC 规则。
- 识别计算、格式和结构问题。
- 生成带严重程度和建议动作的问题记录。

产出：

- Excel QC engine。
- Excel QC issue list。
- Excel QC report view。

验收标准：

- 分析师上传 Powerview Excel 输出后，可以发现明显的数据、公式、格式、total/subtotal 问题。

### Phase 3：PPT-only Delivery QC，2 周

目标：

- 实现 PPT 数字和交付质量检查。
- 识别缺失 source、base、period、footnote 的页面。
- 识别数字格式不一致和重复 KPI 冲突。

产出：

- PPT QC engine。
- PPT QC issue list。
- PPT QC report view。

验收标准：

- 项目经理上传 PPT 后，可以在发客户前发现高风险交付问题。

### Phase 4：PPT + Excel Cross-file QC，2-3 周

目标：

- 将 PPT 数字匹配到 Excel 候选来源。
- 应用四舍五入和单位容忍规则。
- 标记不一致、旧数值和无法验证来源的数字。

产出：

- Cross-file matcher。
- Match confidence scoring。
- Cross-file QC report view。

验收标准：

- 用户可以发现 PPT 中与 Excel 不一致、无法追溯来源或可能未同步的关键数字。

### Phase 5：Workplace 试点版本，1-2 周

目标：

- 打包成试点用户可使用的版本。
- 增加报告导出。
- 增加基础使用提示和错误信息。
- 让部分分析师和项目经理进行试点。

产出：

- Pilot-ready app。
- 可导出的 QC Report。
- Pilot feedback log。
- 修订后的规则 backlog。

验收标准：

- 非技术用户可以独立完成一次 QC，并理解导出的 QC Report。

## 12. MVP 成功指标

MVP 成功的标准：

- 分析师可以在使用 Excel 数据前发现数据产出问题。
- 项目经理可以在发送 PPT 前发现交付风险。
- PPT + Excel 检查可以发现重要的旧数值或不一致数字。
- QC Report 对业务用户来说清楚、可操作。
- 整体流程足够快，可以成为团队标准交付前步骤。

建议量化指标：

- 从试点文件中提取至少 90% 的可见业务数字。
- 识别出人工已知高风险数字问题中的至少 70%。
- 常见报告包的 QC 时间控制在 5 分钟以内。
- 帮助试点用户减少至少 30% 的人工 QC 时间。

## 13. 待确认事项

开始开发前需要确认：

1. 部署方式：内网 Web App 还是本地桌面 App。
2. 文件安全策略：文件是否可以上传到内网服务器，还是必须本地处理。
3. 第一批规则：Data Output QC 和 Delivery QC 的 Top 30 规则。
4. 导出格式：Excel、PDF，或两者都要。
5. 试点用户和试点样例文件。

## 14. 推荐下一步

建议从 Phase 0 开始。当前最重要的工作不是直接开发，而是定义第一批规则，并用真实 Worldpanel 文件验证这些规则是否有价值。

Phase 0 workshop 建议产出：

```text
1. 10-20 组样例 Excel/PPT 文件
2. Top 30 QC 规则
3. 严重程度定义
4. 四舍五入和容忍标准
5. QC Report 模板
6. 试点成功标准
```
