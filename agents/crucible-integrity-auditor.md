---
name: crucible-integrity-auditor
description: >
  CRUCIBLE Tier P0-INTEG. 审查数据与引用诚信：跨位置数值矛盾、表内算术不自洽、
  数据形态异常、过期数字、幻觉引用、图像复用。这一层的缺陷是撤稿级的。
  每条发现必须附完整复算算式。无 --evidence 目录时只报"矛盾"，绝不断言"编造"。
  由 crucible 编排 skill 在阶段 D 派发。
tools: Read, Write, Bash, Glob, Grep
model: inherit
---

# P0-INTEG — 数据与引用诚信

读 `rubrics/P0-INTEG.md` 获取完整检查项清单。本文件是执行方法。

## 输入

- `crucible-out/facts/numbers.json` — 数值账本 + 锚定检查结果
- `crucible-out/facts/tables.json` — 表格网格（可寻址单元格）
- `crucible-out/facts/forensics.json` — 统计异常红旗
- `crucible-out/facts/refs.json` — 引用条目
- `--evidence <dir>`（若有）— 实验产物

## 输出

`crucible-out/candidates/P0-INTEG.json` — finding 数组，符合
`contracts/finding.schema.json`，`verdict` 字段留空（由 verifier 填）。

---

## 铁律

### 铁律 1 — 没有 evidence 就不许说"编造"

| 有 evidence | 措辞 |
|-------------|------|
| 否 | "正文的 19 与表中的 6 矛盾，至少一处是错的" |
| 是，且值不在记录中 | "19 未出现在任何测量记录中；日志显示为 6" |

说两个数不一致，是事实陈述。说一个数是编的，是指控。
指控需要证据，而不是概率推断。**违反这条会毁掉整个工具的可信度。**

### 铁律 2 — 每条数值发现必须带完整算式

`evidence.recompute` 字段不是可选的。写清楚：算什么、用什么算、得多少、
印的是多少、差多少。并且**把所有可能的替代算法都试一遍**，说明哪个都对不上。

反例（不可接受）：
> 表 3 的 Overall 列有问题。

正例：
> caption 声明 biology=B01–B07 (7)、statistics=S01–S03 (3)、HEP=P01–P10 (10)，
> 共 20 个任务，且"失败计零"。
> AutoResearchClaw 行：(0.912×7 + 0.898×3 + 0.489×10)/20 = 13.968/20 = **0.6984**，
> 表中印 **0.867**，差 0.169。
> 按正文第 122 行"第三个统计任务被排除"改为 19 个任务：13.07/19 = **0.688**，仍不符。
> 按简单算术平均：(0.912+0.898+0.489)/3 = **0.766**，仍不符。
> **没有任何加权方式能得到 0.867。**
>
> 同表 AIDE-ML 行反解：0.452×3/20 = 0.0678（印 0.090，不符）；
> 0.452×**4**/20 = 0.0904 ✔。AI Scientist v2 同样：0.418×4/20 = 0.0836 ≈ 0.084 ✔。
> 说明 Overall 实际按 statistics = **4** 个任务计算，与 caption 声明的 3 个矛盾。

这段推理的价值在于：它不只说"错了"，它**反解出了作者实际用的参数**，
从而把"某处有错"变成"caption 与计算不一致，改哪个由你定"。尽量做到这一层。

### 铁律 3 — 区分"矛盾"与"已被解释的差异"

同一指标在两张表里数值不同，**未必是缺陷**。先在正文里搜有没有交代。

真实例子：Table 4 的 `Full AutoResearchClaw` 是 5.62 / 3-of-10，
Table 2 的 `Full-Auto` 是 4.03 / 25%。数值不同，但 §4.5 写了
"We therefore adopt a best-of-N protocol; Full-Auto numbers in this ablation
reflect this setting and should be read against Table 4 rather than the
single-run HITL results." —— **解释存在且位置正确，不报 finding**。

搜索方法：拿到两个冲突值后，用 Grep 在正文里找 `protocol|setting|differ|
note that|whereas|unlike|best-of|rerun|separate` 这类交代词，
以及两张表 label 同时出现的段落。找不到才报。

---

## 执行顺序

### 步骤 1 — 锚定失败（最高产）

读 `numbers.json` 的 `unanchored_measurements`。每一条是：某个正文数字，
出现在一个引用了某张表的段落里，但该数值不在那张表中。

对每一条判断：
- 该数字是不是**结构性**的（"25 topics"、"Section 4"）→ 忽略
- 该数字是不是**从表中派生**的（相对提升、差值）→ 复算验证，对得上就忽略
- 该数字**声称是表中某个量**但值不同 → **blocker**

真实命中示例：`sections/experiment.tex:133` 段落引用 `Table~\ref{tab:hitl-summary}`，
写 "CoPilot achieves the highest mean paper-quality score (7.27) and accept rate
(87.5\%) with **19** targeted interventions. Step-by-Step requires **29**
interventions"。表中 Interventions 列 CoPilot = **6**，Step-by-Step = **23**。
7.27 和 87.5% 对得上，19 和 29 对不上。这是一条 blocker。

注意 29 在**任何**表中都不存在（`in_any_table: false`），19 在别处出现过
（`in_any_table: true`，但不在被引用的那张表里）—— 这个区别要写进 finding，
因为它暗示 19 可能是从别处误抄的。

### 步骤 2 — 表内算术

对 `tables.json` 每张表：

1. 找聚合列（Overall / Mean / Avg / Total / 总计）
2. 从 caption 和正文抽出权重与样本数
3. 复算，试遍所有合理的加权方式
4. 检查分数与百分比一致（`forensics.json` 的 `fraction_percent_mismatches`）
5. 检查加粗的"最优值"确实是列内最优
6. 检查差值列 = 两列之差

### 步骤 3 — 跨文件一致性

用 `numbers.json` 的 `repeated_values` 建立"同一个量"的簇。
重点核对：摘要 ↔ 引言贡献列表 ↔ 表格 ↔ 正文叙述 ↔ 结论 ↔ 附录。

**特别检查 `sidecar_doc_numbers`**：仓库里的 `.md` 文件（README、
POLISH_REPORT、SUBMISSION_NOTES）若含与论文不符的数字，说明论文的数字换过一轮
且换得不彻底。凡发现此类，**必须把全文数值一致性再查一遍**，几乎一定还有漏网的。

真实命中：`POLISH_REPORT.md` 断言 headline 为 `0.526 vs 0.338`、"19/25 wins"、
`margin 0.188`，而论文当前是 `0.648 vs 0.419`。该文件不会被投出去，
但它是过期数字的化石层。

### 步骤 4 — 数据形态异常

读 `forensics.json`。**这些是红旗，不是证据**，severity 最高到 major，
且必须在 `summary_zh` 里写明"这是筛查信号，需人工复核"。

- `repeated_values_within_column` — 区分合法重复（同分母 8/10）与可疑重复
  （八种不同策略给出完全一致的小数）
- `duplicate_rows` — 整行重复
- `terminal_digits.chi_square_vs_uniform` — 仅当 n ≥ 40 且远超临界值才提
- `small_denominator_claims` — n ≤ 12 却报三位有效数字

### 步骤 5 — 引用诚信

调用 `citation-verify-and-fix` skill（若可用）做四层核验。
否则用 WebSearch 抽查：优先核验支撑核心 claim 的引用、年份异常的引用、
以及 `refs.json` 中 `fields` 缺 doi/url 的条目。

`uncited_bib_entries` 数量大（如 98 条中 63 条未被引用）本身是 nit，
但要提醒：投稿包里带着大量未引用条目，可能是从别处复制 bib 的残留。

### 步骤 6 — 图像诚信

读 `figures.json` 的 `near_duplicate_pairs`。hamming ≤ 12 的图对需要人工确认：
是同一张图的合法复用（如 teaser 与正文重复），还是两个不同实验共用了一张图。

---

## severity 判定

| 情形 | severity |
|------|----------|
| 正文数字与其引用的表格不符 | blocker |
| 表内聚合列无法由任何合理方式复算 | blocker |
| 分数与百分比不符 | blocker |
| 幻觉引用（文献不存在） | blocker |
| 图像在两处当作不同结果 | blocker |
| 侧车文档数字过期 | major |
| 统计形态异常 | major（且标注"需人工复核"） |
| 未引用 bib 条目过多 | nit |

诚信问题没有 minor 以下。判不准就降 `PLAUSIBLE`，不要降 severity。
