# Worldpanel 行业规则与 AI 辅助审核设计

## 目标

为 Worldpanel Data QC Assistant 增加面向市场调研与快消品数据的业务审核能力。产品仍然支持单 Excel、单 PPT、单 PDF，以及 Excel 与 Slides 混合检查。所有疑点都由用户逐条确认，不自动修改原始文件。

## 审核结构

产品采用三层审核：

1. **稳定硬规则**：本地运行，可解释、可重复验证，用于识别明确的数据关系错误。
2. **品类模板**：向 AI 提供快消品品类背景和风险重点。第一版支持通用快消品、生鲜、饮料、乳制品、个护。
3. **AI 行业审核**：把完整解析数据、硬规则疑点和 Slides 视觉页面发送给已配置模型，利用模型对市场调研与快消品行业的历史经验识别异常值、市场常识问题、标注问题和跨表逻辑问题。

AI 结论属于辅助判断，必须由用户确认。

## 第一版硬规则

- `Volume ≈ Buyers × Volume per Buyer`
- `Volume per Buyer ≈ Frequency × Volume per Occasion`
- `Spend ≈ Volume × Price`
- `Buyers ≈ Households × Penetration`
- `Spend per Buyer ≈ Volume per Buyer × Price`
- `Spend per Occasion ≈ Volume per Occasion × Price`
- Share、Contribution Share 在同一口径内加总应接近 `100%`
- Share、Penetration 的值应在 `0%` 到 `100%` 范围内
- 均价等连续指标检查同一产品跨期异常跳变
- 提示单位、百分比、小数位、数量级、标注与名称不一致风险

考虑到 PowerView 导出表可能有不同单位，恒等式采用相对误差检查，并在数量级明显不一致时提示人工确认，不自动判定原始值错误。

## AI 审核重点

模型收到：

- 文件完整解析数据
- 本地规则疑点
- Worldpanel 指标定义与恒等式
- 当前品类模板
- Slides 页面图片，用于检查图片、图表、标题、脚注和标注

AI 需要检查：

- 与同产品历史表现或同类产品差异过大的异常值
- 价格、销量、金额、渗透率、频次之间不符合常识的变化
- 表内、表间、Excel 与 Slides 之间的口径或数字不一致
- 图表标题、单位、图例、脚注、时间范围与数据之间的不一致
- 可能由单位、小数位、复制粘贴或标注错误引起的问题

## Slides 视觉覆盖

存在图片、组合对象或图表的 Slides 页面进入视觉审核。结构化图表即使能够读取底层数值，也仍需要截图交给模型检查视觉展示与标注。

## 结果呈现

疑点报告继续按文件、Sheet 或 Slides 页码定位。每条疑点提供：

- 严重程度
- 规则来源
- 数据位置
- 证据
- 建议复核动作
- 用户逐条确认状态

