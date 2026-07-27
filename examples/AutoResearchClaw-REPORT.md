# CRUCIBLE 审查报告 — AutoResearchClaw

**稿件**：`AutoClaw_for_NIPS.zip`（8 个 tex 文件，1383 行，49 节，14 个浮动体，98 条 bib）
**编译主文件**：`main.tex`（`\documentclass{fairmeta}`）
**会场**：NeurIPS 2026 Main Track，规则核实于 2026-07-27
**证据目录**：未提供 —— **本报告只报"矛盾"，不断言"编造"**
**采集耗时**：32 秒（8 个采集器）

> ⚠️ **两个前提假设，若不成立则相关结论作废**
> 1. 仓库有两个主文件（`main.tex` / `main-nips.tex`），本次编译的是 `main.tex`。
>    若投的是另一个，篇幅与样式类结论需重跑。
> 2. 本报告按**双盲投稿版**审查。若这是 camera-ready 或 arXiv preprint，
>    Tier V 的全部匿名类结论作废。

---

## 摘要

| Tier | blocker | major | minor | nit |
|------|--------:|------:|------:|----:|
| P0-BUILD | 1 | 3 | 1 | 0 |
| P0-INTEG | 2 | 1 | 0 | 1 |
| P0-SURF | 0 | 1 | 1 | 0 |
| P2-RIGOR | 1 | 3 | 0 | 0 |
| P4-PRES | 0 | 1 | 1 | 1 |
| V-VENUE | 5 | 1 | 0 | 0 |

**一句话结论**：按现状投 NeurIPS 2026 会**在进入评审前被拒**（篇幅、样式、
checklist、匿名四项各自独立构成 desk reject 理由）。即便这些全部修好，
表 4 的 Overall 列存在一个**无法由任何加权方式复算出来的数字**，
且偏差方向对作者有利 —— 这是整份报告里最需要立刻处理的一条。

---

# ⛔ 必须修（blocker）

## [P0-INTEG-001] 表 4 的 Overall 列无法复算，且各行用了不同的加权

**位置**：`sections/experiment.tex:108`（表 `tab:scidomain`）

**caption 原文**：
> We evaluate biology on B01--B07, statistics on S01--S03, and HEP-ph on P01--P10.
> Failed runs are counted as zero when computing the run-weighted overall mean
> over the 20 science-domain tasks.

即声明：biology = 7 个任务，statistics = 3 个，HEP = 10 个，共 20 个，失败计零。

**复算**：

```
AutoResearchClaw (CoPilot) 行  [bio=0.912, stat=0.898, hep=0.489, 印 Overall=0.867]
  按 caption (stat=3, N=20):        (0.912×7 + 0.898×3 + 0.489×10)/20 = 0.6984
  按正文"第三个统计任务被排除":       (0.912×7 + 0.898×2 + 0.489×10)/19 = 0.6879
  按反解出的 stat=4, N=20:          (0.912×7 + 0.898×4 + 0.489×10)/20 = 0.7433
  三列简单算术平均:                  (0.912 + 0.898 + 0.489)/3        = 0.7663
  ──────────────────────────────────────────────────────────────────
  印出来的值:                                                          0.867

AIDE-ML 行  [bio=✗, stat=0.452, hep=✗, 印 Overall=0.090]
  按 caption (stat=3, N=20):        0.452×3/20 = 0.0678   ✗ 不符
  按 stat=4, N=20:                  0.452×4/20 = 0.0904   ✓ 匹配

AI Scientist v2 行  [stat=0.418, 印 Overall=0.084]
  按 caption (stat=3, N=20):        0.418×3/20 = 0.0627   ✗ 不符
  按 stat=4, N=20:                  0.418×4/20 = 0.0836   ✓ 匹配
```

**穷举验证**：对 (bio, stat, hep) 三个整数权重在 0–20 范围内穷举 9261 种组合，
能得到 0.867 的有 25 种，**其中 HEP 权重全部落在 {1, 2, 3, 4}**。
而 caption 声明 HEP = P01–P10，是任务数**最多**的一档（10 个）。

**问题**（两条独立缺陷，合并为一条 finding）：

1. **两个 baseline 行的 Overall 与 caption 不一致** —— 它们精确对应
   "statistics = 4 个任务"，而 caption 写的是 `S01–S03`（3 个）。
2. **本方法行的 Overall 与任何一种加权都不一致** —— 包括与两个 baseline
   自己所用的那一种。在 baseline 的加权方案下本方法应为 **0.7433**，
   印出来是 **0.867**，高 0.124（相对 +16.7%）。

**为什么这是 blocker**：同一张表内，作者自己的系统与被比较的系统用了
不同的计算方式，且差异方向对作者有利。这张表是"跨领域覆盖"这一核心 claim
的唯一证据。审稿人一旦自己算一遍（这类表格审稿人是会算的），
这篇稿子的可信度会立刻崩塌。

**建议**：
- 若 0.867 有正确来源，请在 caption 中写明真实的加权方案与任务数。
- 若加权应为 caption 所述，三行 Overall 都需要重算。
- 无论哪种，caption 的 `S01–S03` 与实际使用的统计任务数必须一致。

---

## [P0-INTEG-002] 正文的干预次数与它引用的表格不符

**位置**：`sections/experiment.tex:133`（该段开头即引用 `Table~\ref{tab:hitl-summary}`）

**原文**：
> CoPilot achieves the highest mean paper-quality score (7.27) and accept rate
> (87.5\%) with **19** targeted interventions. Step-by-Step requires **29**
> interventions but achieves only 5.19 and 50\%.

**复算** —— 表 `tab:hitl-summary` 的 Interventions 列：

| Mode | 表中值 | 正文值 |
|------|-------:|-------:|
| Full-Auto | 0 | — |
| Gate-Only | 3 | — |
| **CoPilot** | **6** | **19** ✗ |
| Thorough | 8 | — |
| **Step-by-Step** | **23** | **29** ✗ |
| Pre-Experiment | 3 | — |
| Post-Experiment | 3 | — |

同段的 `7.27` 与 `87.5%` 与表**一致**，只有干预次数对不上。

**补充信号**：`29` 在论文的**任何**表格中都不存在；`19` 在别处出现过。
这暗示两个数可能来自某个更早的版本或另一次统计口径。

**建议修改**：
> ...with 6 targeted interventions. Step-by-Step requires 23 interventions...

**连带位置**：修改后请核对摘要与引言中是否引用了同一组数字。

---

## [P0-BUILD-001] 被 `\input` 的章节文件已被掏空，该节从 PDF 中消失

**位置**：`main.tex:167` → `sections/analysis.tex`

`main.tex` 仍执行 `\input{sections/analysis}`，但该文件只剩两行注释：

```latex
% Analysis content merged into Section 4 (Experiments).
% Artifact-level effects, compile health, and limitations moved to Appendix.
```

编译不报错，PDF 里这一节直接不存在。注释说明内容"已并入第 4 节"，
所以这很可能是**有意的重构留下的空壳**，而不是内容丢失。

**建议**：删除 `main.tex:167` 的 `\input` 行与该文件，或恢复内容。
保留一个空 `\input` 只会让下一个协作者困惑。

---

## [P2-RIGOR-001] 表 3 各行的有效样本数不同，行间均值不可比

**位置**：`sections/experiment.tex:52`（表 `tab:hitl-summary`）

| Mode | Valid | Mean Q | Accept |
|------|------:|-------:|-------:|
| Full-Auto | 8/10 | 4.03 | 25.0% |
| Gate-Only | 10/10 | 5.03 | 50.0% |
| **CoPilot** | **8/10** | **7.27** | **87.5%** |
| Thorough | 7/10 | 4.86 | 42.9% |
| Step-by-Step | 10/10 | 5.19 | 50.0% |
| Pre-Experiment | 8/10 | 4.28 | 37.5% |
| Post-Experiment | **6/10** | 5.08 | 50.0% |

**问题**：`Mean Q` 与 `Accept` 各自在**不同的 topic 子集**上计算，分母从 6 到 10 不等。
失败的 topic 很可能系统性地更难，因此各 mode 面对的难度分布不同，
边际均值之间**不构成合法比较**。

Post-Experiment 只有 6/10 有效却报 50% accept；CoPilot 8/10 有效报 87.5%。
这张表支撑摘要的核心 claim（"targeted collaboration consistently outperforms
both full autonomy and exhaustive step-by-step oversight"）。

**论文其实已经部分处理了**：正文写了
> On matched topics, CoPilot beats Full-Auto by $+3.21$ and beats Step-by-Step by $+2.16$.

配对比较是正确的做法。但**主表和摘要用的仍然是不可比的边际均值**，
所以缺陷成立。

**建议**：把配对比较提升为主结果（表中增加"全 mode 均成功的 topic 交集"列，
或直接以配对差值作为主指标），边际均值降为附录。

---

## [V-VENUE-001~005] Desk-reject 风险（五项独立成立）

见 `DESK_RISK_CARD.md`。摘要如下：

| # | 检查 | 结果 | 依据 |
|---|------|------|------|
| 1 | 篇幅 | ⛔ 11 / 9 页 | References 起于 PDF 第 11 页 |
| 2 | 样式完整性 | ⛔ 34 处负间距，33 处紧邻章节命令 | system 14 / experiment 13 / intro 4 / conclusion 2 / related_work 1 |
| 3 | Checklist | ⛔ 未出现在 PDF 中 | `main.tex:181` `% \input{checklist}`，而 `checklist.tex` 有 5345 字节且**已完整填写** |
| 4 | 匿名 | ⛔ | `main-nips.tex:5` `\usepackage[final]{neurips_2026}`；36 个 `\author`、13 个机构、`\{jqliu,shiqiu,huaxiu\}@cs.unc.edu`、`github.com/aiming-lab` |
| 5 | 主文件唯一性 | ⛔ 2 个候选 | `main.tex`（fairmeta，**未用** neurips_2026.sty）/ `main-nips.tex`（用了） |

**第 3 项特别值得注意**：checklist 已经写好了，只差主文件里的三个 `%`。
任何扫描源码目录的检查都会认为它存在。**只有编译出 PDF 再检查才能发现它不在成品里。**

**第 2 项的修复有连锁后果**：删掉 34 处负间距会**增加**页数，
而当前已超限 2 页。正确的修复顺序是：先删负间距 → 重测页数 → 再决定削减哪部分内容。
不要只删了事。

---

# ⚠️ 应该修（major）

## [P0-INTEG-003] 仓库内文档保留着上一版的数字

`POLISH_REPORT.md` 断言 headline 为 `0.526 vs 0.338`、`19/25 wins`、`margin 0.188`。
论文当前的对应数字是 `0.648 vs 0.419`（相对提升 54.65%，绝对差 0.229）。
`0.526 / 0.338 / 0.188 / 19/25` 在论文正文中**一处都不存在**。

这些文件不会被投出去，但它们是**过期数字的化石层** —— 说明论文的数字换过一轮，
而这一轮换得不彻底。`P0-INTEG-002` 的 `19` 很可能就是同一次换版的残留
（注意 `19/25 wins` 里也有一个 19）。

**建议**：删除或更新仓库内的过程性文档；并把全文数值一致性再查一遍。

## [P0-BUILD-002] 编译存在可恢复错误

```
Package microtype Error: Disabling ligatures of a font is only possible
                         with pdftex version 1.30 or newer.
```

`fairmeta.cls:25` 调用了 `\DisableLigatures`，该命令仅 pdfTeX 支持。
在 XeTeX/LuaTeX 下编译必须开 `continue-on-errors` 才能产出 PDF。
Overleaf 默认 pdfLaTeX 不受影响，但若会场或协作者用其他引擎会失败。

**建议**：确认目标引擎；若需跨引擎，用 `\ifPDFTeX` 包裹该调用。

## [P0-BUILD-003] 两个浮动体从未被正文引用

- `sections/appendix.tex:59` — Algorithm「AutoResearchClaw: Autonomous Research Pipeline...」
- `sections/appendix.tex:421` — Table 9「ARC-Bench topic list (T01–T25)」

审稿人会问这些是干什么的，或认为是在凑篇幅。**建议**：在正文加 `\ref`，或移除。

## [P0-SURF-001] 拼写错误

`sections/experiment.tex:82`：
> ...MadGraph parton-level **generatio**, and quantitative reproduction...

**修复**：`generatio` → `generation`（机械修复，可自动应用）

## [P2-RIGOR-002] 竞品的环境配置失败被计为 0 分并纳入均值

表 4 中 AIDE-ML 与 AI Scientist v2 在 biology / HEP 两列标 ✗，caption 定义为
"code-execution failure caused by missing or unusable domain-specific software"，
并明确"失败计零"纳入 Overall。

"**跑不起来**"与"**不适用于该任务**"是两件事。前者可能是配置问题，后者才是方法局限。
把对手的环境配置失败计入其平均分，再宣称自己 Overall 领先（0.867 vs 0.090），
是一个会被直接攻击的设计选择 —— 尤其当被比较系统的作者很可能就是审稿人时。

**建议**：同时报告"排除失败任务后的均值"作为敏感性分析，并说明为何认为
装不上依赖是被测系统的局限而非实验设置的局限。

## [P2-RIGOR-003] LLM 评委缺少与人类判断的一致性验证

论文核心指标由 LLM 评委产生。已有的是**评委之间**的一致性：
> Two independent agent reviewers run the strict judge in parallel; per-leaf
> disagreements exceeding $|\Delta| > 0.20$ are re-adjudicated.

两个 agent 互相一致，不等于对齐人类判断。此外评委与被测系统同源
（都基于 GPT-5.3-codex），存在自我偏好风险。整篇论文的结论悬在这个未验证的假设上。

**建议**：在一个子集上做人类标注，报告与 LLM 评委的相关性（如 Spearman ρ 或 κ）。

## [P4-PRES-001] 案例研究图中的嵌入截图在最终尺寸下约 1.2pt，不可读

**位置**：`sections/experiment.tex:187`，`figures/casestudy.png`

这条是本报告方法上最值得说明的一条：**该图的有效 DPI 是 761，远超 300 的标准，
但它依然不可读。**

```
源图:        4542 × 2401 px
版面实测:     5.967 in 宽（从编译后 PDF 的图像放置矩形量出）
有效 DPI:    4542 / 5.967 = 761.2  ✓ 通过 DPI 检查

对 300dpi 裁切图做水平投影，测量文字行高:
  检出文字行 21 行
  第 10 百分位行高 = 0.72 pt
  中位行高        = 5.04 pt
  阈值            = 6 pt（正文约 10pt）
```

原因：图里嵌入的是论文表格/图表的**截图**，这些截图本身分辨率不低，
但整张图缩到 5.967 英寸后，截图里的文字就只剩 1–5pt。
标注气泡（"All 8 CV strategies report identical 0.0 bias"）是大字，读得清；
被标注的**证据本身**读不清。

**建议**：截图部分只保留能读清的关键行（放大裁切），或改为重绘的示意表格，
或把该图改为整页宽（会与篇幅冲突，见 V-VENUE-001）。

## [V-VENUE-006] 没有以 "Limitations" 为标题的章节

PDF 中不存在标题为 Limitations 的章节。

**但这条不是 blocker**：局限性在 Appendix J（`sec:ethics`）与失败分析附录中有实质讨论，
`checklist.tex` 也指向了这两处。NeurIPS 要求有局限性讨论，未强制标题。

**建议**：若采纳 checklist（见 V-VENUE-003），确保其中 Limitations 项的
Justification 指向的小节确实存在且内容匹配 —— 在强制声明中作不实陈述，
比缺 checklist 更严重。

---

# 📝 可以修（minor / nit）

## [P4-PRES-002] 同一符号在两张表中含义相反

`\xmark`（红叉）在表 4 表示"执行失败"（坏事），
在表 5 的 Fabrication 列表示"未发生造假"（好事）。
快速浏览的审稿人会误读。**建议**：Fabrication 列改用 "None" / "Present" 文字。

## [P0-SURF-002] Benchmark 名称三种写法混用

`\bench{}`（渲染为 ARC-Bench）、`ARC-BENCH`、`ARC-Bench` 并存
（如 `experiment.tex:145` 的 "the same 10 ARC-BENCH topics"）。
不影响正确性，但会降低"这稿子被认真检查过"的印象。

## [P0-BUILD-004] `sections/ethics.tex` 是 0 字节的死文件

仅在 `main-nips.tex:178` 被引用，且已被注释掉。**建议**：删除。

## [P4-PRES-003 / nit] 投稿包内有未被使用的图片

`figures/framework.png`（3.7 MB）、`figures/logo.png`（779 KB）没有任何
`\includegraphics` 引用它们。**建议**：从提交包中移除。

## [P0-INTEG-004 / nit] 98 条 bib 中 63 条未被引用

不影响编译，但可能是从别处复制 bib 的残留。

---

# ✅ 已通过的检查

**这一节不能省。只列缺点的报告让作者无法判断哪些地方已经安全。**

| 检查 | 结论 |
|------|------|
| **摘要 54.7% 的主张** | (0.648 − 0.419)/0.419 = **54.65%**，与摘要、引言、结论四处**完全一致** ✓ |
| **交叉引用完整性** | 40 个 `\ref` 全部解析，46 个 `\cite` 全部在 bib 中，0 个重复 label，0 张缺失图片 ✓ |
| **渲染健康** | 0 处 >5pt 的 hbox 溢出；PDF 文本层中 0 个 `TODO`/`FIXME`/`??`/lorem ipsum ✓ |
| **R1.2 比较公平性** | "All frameworks use the same LLM backbone (GPT-5.3-codex) and the same sandboxed execution environment with identical per-experiment time budgets." 同 backbone、同沙箱、同预算，控制到位 ✓ |
| **R4.1 best-of-N 披露** | §4.5 明确说明协议并指出该设定仅适用于表 5，位置正确、表述清晰 ✓ |
| **表 5 与表 3 的数值差异** | `Full AutoResearchClaw` 5.62 vs `Full-Auto` 4.03 数值不同，但 §4.5 已交代原因（best-of-3 vs 单次）—— **已被解释的差异不是缺陷**，不报 finding ✓ |
| **F1.1 图片分辨率** | 3 张图有效 DPI 分别为 645 / 415 / 761，全部超过 300 ✓（但见 P4-PRES-001：DPI 不等于可读性） |
| **F4.6 脚注标记** | 表 5 的 `$^{\ddagger}$~Score inflated by removing the verification gate.` 有明确解释 ✓ |
| **D2.6 前作归属** | 论文诚实写明 "the ColliderAgent architecture we directly adopt here"，未把前作能力据为己有 ✓ |
| **主图可读性** | `main_figure.png` 中位文字 11.04pt，第 10 百分位 6.48pt，可读 ✓ |

---

# 修复分类

| finding | 类型 | 处理 |
|---------|------|------|
| P0-SURF-001 `generatio` | mechanical | ✅ 可自动修复 |
| P0-BUILD-001 空 `\input` | mechanical | ✅ 可自动修复（删除该行） |
| P0-BUILD-004 死文件 | mechanical | ✅ 可自动修复 |
| P0-SURF-002 命名统一 | mechanical | ✅ 可自动修复（逐处确认后） |
| V-VENUE-003 checklist | mechanical | ✅ 取消 `main.tex:181` 的注释 |
| P0-INTEG-002 干预次数 | **judgment** | 📋 改数字需作者确认哪个是真值 |
| P0-INTEG-001 表 4 Overall | **judgment** | 📋 需作者提供正确加权方案 |
| P0-INTEG-003 过期文档 | judgment | 📋 删还是更新由作者定 |
| P2-RIGOR-001 分母不可比 | judgment | 📋 需重组表格结构 |
| P2-RIGOR-003 评委校准 | **requires-experiment** | ⏸ 需人类标注子集 |
| V-VENUE-001 篇幅 | judgment | 📋 削减内容是作者取舍 |
| V-VENUE-002 负间距 | judgment | 📋 删除会加剧超页，需与篇幅一起处理 |

---

# 审稿人模拟（P5）

> 本节为语言模型模拟，**与真实审稿分数的相关性未经验证**。
> 用途是给弱点排序，不是预测录用结果。本报告不输出接收概率。

*（本次为系统验证运行，仅跑了确定性采集器与 P0–P4/V 的分析；
P5 四角色面板在完整 `/crucible` 运行中产出，见 `panel/{ac,r1,r2,r3}.md`。）*

**基于已确认 findings 的弱点分诊**：

| 档 | 条目 |
|----|------|
| **A — 截稿前可修** | P0-SURF-001/002、P0-BUILD-001/003/004、V-VENUE-003/005、P4-PRES-002 |
| **B — 需补实验** | P2-RIGOR-003（人类评委校准） |
| **C — 只能 rebuttal 辩护** | P2-RIGOR-002（失败计零的合理性） |
| **D — 只能认，建议主动写进 limitations** | P2-RIGOR-001 的残余部分（N=10 的统计功效） |

> D 档的处理原则：**主动承认的局限，杀伤力远小于被审稿人抓出来的局限。**

---

# 附：采集事实索引

```
final/facts/ingest.json      8 文件 / 1383 行 / 49 节 / 14 浮动体 / 48 label
final/facts/render.json      24 页，正文 11 页，References p11，Appendix p14
final/facts/tables.json      11 张表，已解析为可寻址网格
final/facts/refs.json        40 ref / 46 cite / 98 bib / 63 未引用
final/facts/numbers.json     381 个正文数字，13 个锚定失败
final/facts/figures.json     3 张图，含版面实测 DPI 与文字行高
final/facts/forensics.json   106 个数值单元格，19 处小分母主张
final/facts/venue.json       NeurIPS 2026 符合性
final/preview/page-NN.png    24 张逐页渲染图
final/figures/fig-NN.png     3 张 300dpi 图表裁切
```

全部数字均可由 `python3 bin/collect.py <repo> -o <out> --venue neurips-2026` 复现。
