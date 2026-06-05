# Worldpanel Data QC Assistant 智能检查范围与输出升级设计

## 背景

当前版本已经可以处理 Excel、PPTX、PDF 的本地规则检查、AI 逻辑检查、Slides OCR、PPT-Excel 数字匹配、结果导出和多人试用。随着真实文件变大，主要问题变成：

- 检查前没有明确任务边界，导致全量 AI 检查耗时很长。
- Source Matching 展示了大量“正常匹配”，用户更关心疑点和冲突。
- 同类错误会分散在多个 issue 中，结果不够适合汇报。
- 输出语言不能按交付对象选择。
- 失败恢复或重复上传时会重复解析、重复调用 AI。

本版本目标是把这些需求统一成一个完整的“智能检查任务设定 + 高效结果输出”流程。

## 目标

1. 在正式检查前，让用户明确本次检查目的、输出语言、检查范围和重点指标。
2. 由 AI 基于文件概览追问边界问题，避免不必要的全量检查。
3. 保留现有检查能力，但用 run scope 控制 AI 深度检查范围和展示重点。
4. Source Matching 默认只汇报疑点、冲突和需要人工确认的地方。
5. 将错误按类型汇总，顶部展示 grouped summary，明细仍可展开。
6. 输出 Excel/PDF 时支持中文、英文、双语。
7. 在不改变现有核心检查逻辑的前提下增加缓存，加快重复检查、失败恢复和相似任务。

## 非目标

- 不在本版本重写现有解析器、规则引擎或 UI 框架。
- 不删除现有明细表，只改变默认展示和导出结构。
- 不强制所有任务都走 AI 追问；用户仍可选择“全量检查并直接开始”。
- 不把缓存作为唯一数据来源；缓存损坏或缺失时必须自动回退到现有逻辑。
- 不在本版本实现永久云端队列或多机分布式处理。

## 用户流程

### 1. 新建 QC Run

用户在项目中点击 `New QC run`，上传文件后进入“检查任务设定”页，而不是立即开始检查。

用户需要填写或选择：

- 输出语言：中文、英文、双语。
- 检查目的：全量检查、指定页/sheet、重点指标、交付前复核、PPT-Excel 对数。
- 是否需要交叉检查：需要、不需要、让 AI 判断。
- 检查重点：价格、share、penetration、volume、spend、注释/标注、单位、小数点、趋势异常。
- 范围提示：页码范围、sheet 名、品牌/品类/客户重点。

### 2. AI 边界澄清

系统先读取轻量文件概览：

- 文件名、类型、大小。
- PPT/PDF 页数和抽样页文本。
- Excel sheet 列表、行列范围和抽样指标。
- 已选择的 project category template。

AI 根据概览生成最多 3 个澄清问题。问题必须是可操作的，例如：

- “是否只检查第 3-10 页和 Summary sheet？”
- “这份 PPT 和 Excel 是否属于同一交付包，需要数字交叉检查吗？”
- “价格异常是否是本次重点，还是只做基础完整性检查？”

用户回答后，系统生成一份 run scope，并展示给用户确认。确认后才进入正式检查。

### 3. 正式检查

正式检查仍调用现有 `run_qc` 主流程，但新增 scope 输入：

- 本地规则仍可扫全量，避免漏掉明显硬错误。
- AI 深度检查只优先处理 scope 指定页、sheet、指标和高风险候选。
- Slides OCR 只处理 scope 指定页和 parser 标记为 review required 的关键页。
- Source Matching 仍会计算候选，但默认只保存或展示疑点。

### 4. 结果查看

结果页新增顶部 `Issue Summary`：

- 按错误类型汇总：价格异常、share 加总、单位/小数点、PPT-Excel 数字冲突、趋势异常、标注/注释问题、品类模板不匹配、文件结构问题。
- 每类展示数量、最高严重度、涉及文件/页码/sheet、推荐处理动作。
- 点击后展开明细 issue。

原 `Current File QC` 仍保留，用于逐条确认状态。

### 5. 导出

用户点击导出时选择：

- 中文
- 英文
- 双语

导出语言影响：

- Excel sheet 名称。
- 表头字段。
- Summary 文案。
- Issue category 名称。
- Recommendation/next action 的汇总表达。

模型原始 evidence 不强制机器翻译；如果选择双语，summary 和 recommendation 双语展示，evidence 保持原始信息并尽量保留上下文。

## 数据模型

### qc_runs 新增字段

- `output_language`: `zh`, `en`, `bilingual`。
- `review_goal`: 用户输入的检查目的文本。
- `scope_status`: `draft`, `needs_clarification`, `confirmed`, `skipped`。
- `scope_json`: AI 生成并经用户确认的检查范围。
- `scope_questions_json`: AI 追问问题和用户回答。

### issues 新增或派生字段

优先不做破坏性迁移。错误分类可先存入 `details_json`：

- `category`: 例如 `price_outlier`, `share_total`, `source_conflict`。
- `group_key`: 用于同类错误归并。
- `group_title`: 汇总标题。

后续如果稳定，再迁移成独立字段。

### 缓存目录

缓存放在 `local_data/cache/`，不进入 GitHub。

建议结构：

- `parse/{file_hash}.json`
- `llm/{model_hash}/{prompt_hash}.json`
- `visual/{file_hash}/page-{page}.png`
- `scope/{files_hash}.json`

缓存 key 必须包含：

- 文件内容 hash。
- 解析器版本或 app cache version。
- 模型名、endpoint host、prompt version。
- run scope。
- category template。

## 组件设计

### Run Scope

新增模块 `worldpanel_qc/qc/scope.py`：

- 构建文件概览。
- 规范化用户输入。
- 解析页码、sheet 和重点指标。
- 判断是否启用交叉检查。
- 将 confirmed scope 转成 runner 可使用的结构。

### AI Scope Assistant

新增模块 `worldpanel_qc/llm/scope_assistant.py`：

- 输入文件概览、用户初始目的、project category。
- 输出最多 3 个问题。
- 输入用户回答后输出 confirmed scope draft。
- 所有返回必须是 JSON，可失败回退为手动 scope。

### Issue Grouping

新增模块 `worldpanel_qc/qc/issue_grouping.py`：

- 根据 `rule_id`、LLM title/description、location、metric、category template mismatch 等信息分类。
- 生成 group summary。
- 同类错误保留明细，但前端和导出优先展示 group。

### Suspicious Source Matching

在现有 `worldpanel_qc/qc/runner.py` 附近增加过滤函数：

- 无候选来源。
- 最佳候选置信度低。
- 多个候选置信度接近。
- 观察值与候选值存在数值冲突。
- 人工确认过的匹配。

正常高置信度匹配不作为默认结果展示，但可在调试模式或后续“show all”中查看。

### Output Localization

新增模块 `worldpanel_qc/reporting/localization.py`：

- 提供中文、英文、双语 label。
- Excel/PDF 导出函数接收 `language` 参数。
- UI 导出按钮传入语言选择。

### Cache Layer

新增模块 `worldpanel_qc/cache.py`：

- 基于 JSON 文件的简单缓存。
- 支持 `get`, `set`, `cache_key_for_file`, `cache_key_for_llm`。
- 缓存失败不影响主流程，只记录 AI log 或 progress detail。

缓存接入点：

- `parse_file` 前后。
- `LlmClient._chat` 或 reviewer 调用层。
- Slides page render 结果。

## 错误处理

- AI 追问失败：允许用户手动选择“直接全量检查”。
- scope JSON 非法：保存原始回答到 AI log，并回退到全量检查。
- 缓存读取失败：删除该缓存文件并重新计算。
- 缓存写入失败：继续检查，不影响 run。
- 导出语言缺失：默认中文。

## 测试策略

### 单元测试

- scope 解析页码、sheet、重点指标。
- AI scope assistant 接受标准 JSON 和 list/string 异常格式。
- issue grouping 能把同类错误汇总，并保留明细。
- source matching 过滤正常匹配，只保留疑点。
- localization 输出中文、英文、双语表头。
- cache key 对文件内容、模型、scope 改变敏感。

### 集成测试

- 新建 run 时进入 scope draft。
- 用户确认 scope 后后台开始检查。
- 全量检查仍兼容旧路径。
- Excel/PDF 导出根据语言返回不同标题。
- 缓存命中时结果与首次运行一致。

## 上线策略

分阶段上线，避免影响当前多人试用：

1. 先上线 scope 表单和导出语言，不默认启用 AI 追问。
2. 再启用 AI scope assistant，失败自动回退。
3. 再启用 suspicious matching 默认展示。
4. 最后启用缓存层，并保留环境变量开关。

建议默认开关：

- `WORLDPANEL_QC_SCOPE_ASSISTANT_ENABLED=1`
- `WORLDPANEL_QC_CACHE_ENABLED=1`
- `WORLDPANEL_QC_MATCHING_SUSPICIOUS_ONLY=1`

## 成功标准

- 用户在开始前能清楚说明检查目的和范围。
- 大文件重复检查时，第二次明显快于第一次。
- Source Matching 页面默认只显示疑点，不再淹没用户。
- 同类错误在结果顶部汇总，适合直接给项目负责人 review。
- 导出报告能按中文、英文、双语输出。
- 现有全量检查能力不被破坏，旧 run 可以继续查看和导出。
