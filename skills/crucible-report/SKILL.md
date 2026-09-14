---
name: crucible-report
description: >
  渲染 CRUCIBLE 的最终报告：报告最前的三档写作来源判断、按严重级别排序的发现清单、一页纸 desk-reject 风险卡、
  claim 账本、修复补丁索引、审稿人模拟意见，并链接 REVISION_PLAN.md。中文叙述 + 英文原文引用。
  由 crucible 编排 skill 在阶段 H 调用；也可在已有 findings.json 的目录上单独重跑。
---

# 报告渲染

## 输入

- `crucible-out/findings.json` — 由 `bin/merge_findings.py` 合并、已带 verdict
- `crucible-out/finding_counts.json` — 摘要表的数字，直接用，不要自己数
- `crucible-out/REVISION_PLAN.md` — 修改建议，报告里链接，不重复抄写
- `crucible-out/panel/*.md` — 审稿人模拟
- `crucible-out/fixes/round-*.json`、`fixes/audit-round-*.json` — 修复记录
- `crucible-out/candidates/*.passed.md` 与 `crucible-out/facts/*.json` — 用于"已通过"小节
- `crucible-out/authorship_assessment.json` — 三档来源判断、支持/反对信号与证据缺口

## 输出

```
crucible-out/
├── REPORT.md
└── DESK_RISK_CARD.md    # 若 venue marshal 已写出则只核对，不重写
```

---

## 排序规则

1. tier 顺序：P0-BUILD → P0-INTEG → P0-SURF → P1 → P2 → P3 → P4 → V → P5
2. tier 内按 severity：blocker → major → minor → nit
3. 同 severity 按 `CONFIRMED` 先于 `PLAUSIBLE`
4. `REFUTED` 不进 REPORT.md，只进 findings.json

## REPORT.md 结构

```markdown
# CRUCIBLE 审查报告 — <论文标题>

## 写作来源判断（非取证结论）

> **档位：<人类主导 / AI深度参与 / 全AI>**
>
> 当前可得证据更符合“<档位>”。这是一项来源风险判断，不是作者身份或诚信的取证结论。

**支持该判断的信号**：
- <strength> — <描述>（`file:line` 或 facts 路径）

**反对信号 / 其他解释**：
- <strength> — <描述>（`file:line` 或 facts 路径）

**缺失证据**：<Git 历史、写作日志、仅有 PDF 等>

**方法限制**：不输出百分比；终稿文风不能可靠区分人类写作、AI 改写与人类重写 AI 初稿。

---

**稿件**：<repo> @ <commit>
**主文件**：<root.tex>（若有多个候选，在此标注确认结果）
**会场**：<venue 或 "未指定，已跳过 Tier V">
**证据目录**：<path 或 "未提供 —— 本报告只报矛盾，不断言编造">
**审查时间**：<date>

## 摘要

| Tier | blocker | major | minor | nit |
|------|--------:|------:|------:|----:|
| P0-BUILD | 1 | 2 | 0 | 0 |
| ... |

**一句话结论**：<现在投出去会怎样>

**先改这三件**（完整顺序见 [REVISION_PLAN.md](REVISION_PLAN.md)）：
1. <取自 REVISION_PLAN.md "先做这些" 前三行>

---

## ⛔ 必须修（blocker）

### [P0-INTEG-001] <中文标题>

**位置**：`sections/experiment.tex:133`

**原文**：
> CoPilot achieves the highest mean paper-quality score (7.27) and accept
> rate (87.5\%) with 19 targeted interventions.

**问题**：<中文说明>

**复算**：
```
表 tab:hitl-summary 的 Interventions 列：CoPilot = 6，Step-by-Step = 23
正文写的是 19 和 29
7.27 与 87.5% 与表一致；仅干预次数不一致
29 未出现在论文任何表格中
```

**审稿人会怎么说**：<一句话>

**建议修改**（judgment，见 `patches/P0-INTEG-001.patch`）：
> ...with 6 targeted interventions. Step-by-Step requires 23 interventions.

**连带位置**：<还有哪里要一起改>

---

## ⚠️ 应该修（major）
...

## 📝 可以修（minor / nit）
...

## ✅ 已通过的检查

**这一节不能省。** 只列缺点的报告让作者无法判断哪些地方已经安全。

- **R1.2 比较公平性** — 同 backbone、同沙箱、同时间预算，控制到位
- **R4.1 best-of-N 披露** — §4.5 明确说明协议，位置正确
- **F1.1 图片分辨率** — 全部 3 张图有效 DPI ≥ 415，超过 300 要求
- ...

---

## 修复状态

| finding | 类型 | 状态 |
|---------|------|------|
| P0-SURF-003 | mechanical | ✅ 已自动修复（`crucible/fixes` 分支） |
| P0-INTEG-001 | judgment | 📋 补丁待批准 `patches/P0-INTEG-001.patch` |
| P2-RIGOR-002 | requires-experiment | ⏸ 需补实验，预计成本 <N> |

---

## 审稿人模拟（P5 — 预测，非事实）

> 以下为语言模型模拟，与真实审稿分数的相关性未经验证。
> 用途是给弱点排序，不是预测录用结果。

| 角色 | 分数 | 主要 weakness |
|------|-----:|--------------|
| AC | 4 | 贡献边界不清 |
| R1 方法学 | 3 | 表 2 各行分母不同，均值不可比 |
| R2 实证 | 4 | 缺少与 X 的比较 |
| R3 怀疑 | 3 | "consistently" 建立在 N=8 上 |

**分歧点**：<四个角色不一致的地方 —— 分歧本身是信息>

弱点分诊（A 可修 / B 需补实验 / C 只能 rebuttal / D 只能认）与回应草稿见
[REVISION_PLAN.md](REVISION_PLAN.md) 的"审稿人可能提出的问题"一节。
完整意见见 `panel/{ac,r1,r2,r3}.md`。
```

---

## 语言纪律

- **叙述用中文，引用的稿件原文、建议替换文本、rebuttal 措辞用英文。**
  用户要能直接把英文段落粘回论文，不必二次翻译。
- 术语保留英文原形（ablation、baseline、blocker、claim、desk reject）。
- 不翻译文件名、宏名、label。

## 数字纪律

- 每条数值发现必须带 `evidence.recompute` 的完整算式，报告里原样呈现。
- 报告自身引用的任何统计（如"34 处负间距"）必须来自 `facts/`，
  不得凭印象写。**一份审查报告自己的数字出错，是最糟糕的失败模式。**

## 分区纪律

P5 与 P0–P4 **分区呈现，不混排**。事实性 finding 和主观预测放进同一个列表，
后者会稀释前者的可信度。P5 段落必须带那句免责说明。

写作来源判断必须是标题后的第一个 section。若 `authorship_assessment.json` 缺失或不符合
schema，不得静默省略：报告顶部写“未完成来源评估”，并把报告视为未完成产物。

生成后必须运行：

```bash
python3 <CRUCIBLE>/bin/validate_report.py crucible-out
```

它检查：来源判断是第一节；REPORT.md 不含 REFUTED 的 id；REVISION_PLAN.md
覆盖所有未自动修复的 blocker / major，且不引用 REFUTED 条目。校验失败时报告尚未完成，修正后重跑。

## 不做的事

- 不给"接收概率"
- 不给总分
- 无 evidence 目录时不使用"编造""fabricated"等词，只说"矛盾""不一致"
