# CRUCIBLE

> 坩埚。矿石入炉，贱金属化为炉渣被烧掉，剩下的才是可发表的东西。
> A crucible is where ore is heated until the base metal separates from the noble.
> It is a purification, an irreversible qualitative change, and — in plain English — a severe test.

CRUCIBLE 是一个 **skills + subagent 驱动**的投稿前论文自查系统。输入一个 Overleaf 仓库
（zip / git / 本地目录），输出一份**按严重级别排序**的缺陷清单、可复算的证据、按先后顺序排好的修改建议，
以及 agent 执行的机械修复。报告标题后的第一节固定给出“人类主导 / AI深度参与 / 全AI”三档
写作来源判断；该判断与 finding severity 分离。

---

## 1. 设计公理

五条规则约束整个系统。违反其中任何一条的产出都不算数。

### 公理 1 — 通用性优先于会场规则 (Universal before contingent)

会场规则每年都变（页数、匿名政策、checklist 表格、style 文件版本）。
**正确性与诚信不变。** 因此 P0 只包含"在任何会场、任何年份都是错的"东西：
编译失败、`??`、数字自相矛盾、编造数据、错别字。

页数超限、匿名违规、缺 checklist 这些**会场符合性检查单列为 Tier V**，
在报告里放在最后，与前面各层的结论互不影响。一篇 NeurIPS 被拒的稿子改投 ICML 时，P0–P5 的结论全部复用，
只有 Tier V 需要重跑。

### 公理 2 — 每条发现必须可复算 (Every finding recomputes)

不接受"感觉不严谨"这类结论。每条 finding 必须带：

- `file:line` 精确定位
- 原文摘录
- **对于数值类发现：完整的复算算式**

> 反例：「表 3 的 Overall 列看起来不对」
> 正例：「表 3 中 `0.912×7 + 0.898×3 + 0.489×10 = 13.968`，除以 caption 声明的 20 个任务
> 得 `0.6984`，与表中 `0.867` 不符。若按正文第 122 行"第三个统计任务被排除"改为 19 个任务，
> 得 `0.688`，仍不符。没有任何加权方式能得到 0.867。」

### 公理 3 — P0/P1/V 的每条发现必须经对抗验证 (Adversarially verified)

发现由审查 agent 提出后，交给一个**独立的 `crucible-verifier`**，其任务是
**证伪**，默认立场是"这条是误报"。只有被证伪失败的发现才进入报告，标记 `CONFIRMED`；
证伪不彻底的标记 `PLAUSIBLE` 并降级。

理由：一个乱报警的审查工具比没有工具更糟——用户会开始无视全部输出，
包括那条真正会导致 desk reject 的。

### 公理 4 — 探测可用脚本，修复必须由 agent 执行 (Detect by script, fix by agent)

`bin/` 下的确定性脚本只负责**采集事实**：抽出所有数字、解析表格网格、量出图片有效 DPI、
统计 `\ref` 与 `\label` 的差集。它们**不下判断**。

判断由 subagent 做，修复也由 subagent 做。永远不用 `sed` 批量替换。
原因很实际：脚本会把 `generatio` 改成 `generation`，也会把某个领域专有名词、
某个作者姓氏、某段 verbatim 代码里的字符串一起改掉。Agent 会先读上下文再动手。

### 公理 5 — 来源判断必须综合证据 (Authorship is provenance, not style)

“AI 味”不是可复核证据。系统只输出三档而不输出百分比，并把直接 disclosure、写作日志、
源码泄漏、版本历史、已验证自洽性异常、人工修订轨迹和反证分开列出。`全AI` 需要直接
provenance 或多条独立的全文级高特异性证据；流畅、套话、词频和单一 detector 分数不够。
该结论是来源风险判断，不是对作者身份或诚信的取证结论。

---

## 2. 严重级别阶梯

报告按下表顺序排列（执行上各层并行，见第 3 节）。P0 未清空时，后续 tier 的结论仍会产出，但报告顶部会标注
「P0 未清零，以下结论可能建立在会被推翻的稿件状态上」。

| Tier | 中文名 | 判据 | 通用? |
|------|--------|------|-------|
| **P0-BUILD** | 构建与渲染 | 稿子能不能正确变成 PDF，PDF 里有没有肉眼可见的破绽 | 是 |
| **P0-INTEG** | 数据与引用诚信 | 数字是不是编的、自相矛盾的、过期的；引用是不是幻觉的 | 是 |
| **P0-SURF** | 表层硬伤 | 错别字、断掉的 `\input`、空的被引文件、坏掉的记号 | 是 |
| **P1-CLAIM** | 主张—证据对齐 | 每个 claim 有没有对应实验；每个机制有没有自己的对照 | 是 |
| **P2-RIGOR** | 实验严谨性 | baseline 强不强、ablation 全不全、有没有误差棒、有没有选择性报告 | 是 |
| **P3-DEF** | 问题定义与新颖性 | 问题定义清不清楚（novelty 争议的根源）、贡献增量是否可辩护 | 是 |
| **P4-PRES** | 呈现质量 | 图在最终尺寸下看不看得清、表格有效数字、caption 自足性 | 是 |
| **P5-PANEL** | 审稿人模拟 | AC + 3 个审稿人格性预测弱点，按"截稿前可修 / 只能认" 排序 | 是 |
| **V-VENUE** | 会场符合性 | 页数、匿名、checklist、style 文件、格式 | **否，报告中单列** |

各 tier 的完整检查项见 `rubrics/`。

### 为什么 P3 叫「问题定义」而不是「新颖性」

Novelty 争议几乎从来不是"这个想法有没有人做过"的事实之争，而是**定义之争**。
审稿人说"这就是 X 的变体"，作者说"不是，我们解决的是 Y"——双方在谈不同的问题，
因为论文从来没有把问题**形式化地**定死。

所以 P3 的第一个检查项不是"搜一下有没有人做过"，而是：
**这篇论文能不能用一句话说清它的输入、输出、约束和成功判据？** 说不清，
novelty 就无法辩护，无论实验多好。

---

## 3. 架构

```
/crucible <paper>                      skills/crucible（编排）
  │
  ├─ A INGEST    解包、确认主文件与稿件用途（需要问用户的都在这里问完）
  ├─ B COLLECT   bin/collect.py → facts/*.json、逐页 PNG、图裁切（确定性）
  ├─ C PREVIEW   编排器逐页看渲染结果
  │
  ├─ D REVIEW    并行波 1，互不依赖、互不可见
  │    build-inspector  integrity-auditor  surface-auditor  claim-auditor
  │    rigor-reviewer   novelty-analyst    figure-critic    venue-marshal
  │    role-ac  role-methodologist  role-empiricist  role-skeptic
  │    长稿时 surface / claim 按章节分片，各片并行
  │         → candidates/*.json、panel/*.md
  │
  ├─ E VERIFY    并行波 2，每条候选一个 verifier，立场是"这条是误报"   ← 公理 3
  │         → verdicts/<id>.json → bin/merge_findings.py → findings.json
  │
  ├─ F FIX       串行，最多 3 轮：fixer → re-collect → fix-auditor       ← 公理 4
  │
  ├─ G SYNTHESIZE 并行波 3
  │    authorship-assessor → authorship_assessment.json
  │    revision-planner    → REVISION_PLAN.md
  │
  └─ H REPORT    crucible-report → REPORT.md → bin/validate_report.py
```

### 为什么这样分波

一篇稿子的主要耗时在审查 agent 读稿。P0–P4 各层读的是不同的 facts，审稿人模拟刻意不看
任何 findings，会场检查只读 `venue.json`，三者之间没有依赖，所以放在同一波并行。
验证必须等候选齐了才能开始，但每条候选的验证彼此独立，所以第二波按条并行。
修复会改稿件，只能串行。来源判断和修改建议都要用验证后的结果，放在最后一波并行。

并行的代价是写冲突。约定是：每个 agent 只写自己名下的文件（`candidates/<TIER>.json`、
`verdicts/<id>.json`、`panel/<role>.md`），合并交给确定性的 `bin/merge_findings.py`。

### 为什么 collect 和 judge 分离

`bin/` 脚本每次运行结果完全相同，可以被 diff、被 CI 跑、被 fix loop 重复调用来证明
修复没有引入回归。如果把"抽数字"这件事交给 LLM，两次运行会抽出不同的集合，
fix loop 就无法判断自己是否改好了。

Agent 负责的是脚本做不了的事：这两个 0.87 是不是**同一个量**、
这个 baseline 是不是**故意选弱的**、这个问题定义**说清楚了没有**。

---

## 4. 证据目录 (`--evidence`)

可选。指向实验产物目录（`runs/*.json`、`results.csv`、日志）。

给了以后，P0-INTEG 从**一致性检查**升级为**真伪检查**：

| 无 evidence | 有 evidence |
|-------------|-------------|
| 「正文说 19，表里说 6，两者矛盾」 | 「正文说 19，表里说 6，实测日志是 6。正文错。」 |
| 「0.867 无法由表内任何加权得到」 | 「0.867 在全部测量记录中不存在。这是一个凭空出现的数。」 |

后者是 CRUCIBLE 唯一能真正断言"这个数是编的"的路径。没有 evidence 目录时，
系统只报矛盾，绝不断言编造——公理 2 不允许无据的指控。

---

## 5. 输出

```
crucible-out/
├── REPORT.md                 # 主报告，中文叙述 + 英文原文引用
├── REVISION_PLAN.md          # 修改建议：先改什么、改哪里、替换文本、工作量
├── DESK_RISK_CARD.md         # 一页纸：会不会当场被拒
├── authorship_assessment.json
├── findings.json             # 结构化，符合 contracts/finding.schema.json，含 REFUTED
├── finding_counts.json
├── candidates/  verdicts/    # 并行审查与验证的原始输出
├── facts/                    # 确定性采集结果（可 diff）
├── preview/  figures/        # 逐页 PNG、每张图 300dpi 裁切
├── ledgers/claim_ledger.md   # claim → 证据位置 → 判定
├── patches/                  # 需人工批准的修改
├── fixes/                    # 每轮修复与审计记录
└── panel/                    # 模拟审稿意见 ac.md r1.md r2.md r3.md
```

机械修复直接提交到 `crucible/fixes` 分支，可 `git diff` 可 `git revert`。

---

## 6. 非目标

- **不代写论文。** CRUCIBLE 不生成新的实验、新的章节、新的 claim。
- **不判断科学价值。** 它不会说"这个方向没意思"。
- **不替代真实同行评审。** P5 的审稿人模拟用来预演弱点，不用来自我背书。
- **无 evidence 目录时不指控造假。** 只报矛盾。
