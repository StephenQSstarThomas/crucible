---
name: crucible
description: >
  论文投稿前的审查与提升系统。输入一个 Overleaf 仓库（zip / git / 本地目录），
  按严重级别阶梯逐层审查：构建渲染、数据诚信、表层硬伤、主张-证据对齐、实验严谨性、
  问题定义与新颖性、呈现质量、审稿人模拟，最后单独跑会场符合性。
  每条发现可复算、可定位、经对抗验证；机械修复由 agent 执行并提交到独立分支。
  TRIGGERS — "审一下我的论文", "投稿前检查", "这篇稿子有什么问题", "review my paper
  before submission", "check this manuscript", "/crucible", 或用户给出一个论文
  仓库/zip 并要求提升质量。
  DO NOT trigger for: 写论文/生成章节（CRUCIBLE 不代写）、单纯的语法润色
  （用 --style-profile 或直接改）、已发表论文的文献综述。
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch
---

# CRUCIBLE

坩埚。矿石入炉，贱金属化为炉渣被烧掉，剩下的才是可发表的东西。

读 `CRUCIBLE.md` 了解设计公理，读 `rubrics/*.md` 了解每层的完整检查项。
本文件是**执行流程**。

---

## 0. 四条公理（不可违反）

1. **通用性优先于会场规则** — P0–P5 与会场无关；页数/匿名/checklist 放在最后的 Tier V。
2. **每条发现必须可复算** — 数值类发现必须给出完整算式，不接受"看起来不对"。
3. **每条 P0/P1 发现必须经对抗验证** — 由独立 verifier 尝试证伪，存活才进报告。
4. **探测可用脚本，修复必须由 agent 执行** — 永远不用 `sed` 批量替换。

---

## 1. 入参

```
/crucible <paper> [--venue <slug>] [--evidence <dir>] [--root <main.tex>]
                  [--double-blind yes|no] [--tiers P0,P1,...] [--no-fix]
```

| 参数 | 含义 | 缺省 |
|------|------|------|
| `<paper>` | zip / git URL / 本地目录 / 单个 .tex | 必填 |
| `--venue` | 会场 profile（`venues/*.yaml`） | 不给则跳过 Tier V |
| `--evidence` | 实验产物目录，启用真伪检查而非仅一致性检查 | 无 |
| `--root` | 指定主文件（仓库有多个 `\documentclass` 时） | 自动探测 |
| `--double-blind` | 是否按匿名投稿审查 | 由 venue profile 决定 |
| `--no-fix` | 只报告不修改 | 关闭（默认执行机械修复） |

**开始前必须确认一件事**：如果仓库里有多个 `\documentclass` 文件，
或 `--venue` 已给出但主文件没用该会场的 style，**先问用户投的是哪一个**。
审错文件的整份报告都是废的。

---

## 2. 阶段

### 阶段 A — INGEST

1. 解包/克隆到工作目录。zip 用 `unzip -q`；git 用 `git clone --depth 1`。
2. 若是用户的真实 Overleaf 仓库，**先建 `crucible/fixes` 分支**（阶段 H 要用）。
   非 git 目录则 `git init` 后提交一次基线，保证修改可回滚。

### 阶段 B — COLLECT（确定性）

```bash
python3 <CRUCIBLE>/bin/collect.py <repo> -o crucible-out \
    [--venue <slug>] [--evidence <dir>] [--root <main.tex>]
```

产出 `crucible-out/facts/*.json` + `crucible-out/preview/page-NN.png`
+ `crucible-out/figures/fig-NN.png`。

**编译失败时不要继续。** 先修编译，因为后面每一层都依赖渲染出的 PDF。
把编译错误作为唯一的 P0-BUILD blocker 报出来，请用户决定。

读 `facts/_summary.json` 先建立全局印象，再按需读具体的 facts 文件。
**不要把所有 facts JSON 一次性读进上下文** —— `numbers.json` 可能上万行。
用 `python3 -c` 或 `jq` 做投影，只取需要的字段。

### 阶段 C — 看预览

**这一步不能跳过。** 用 Read 工具**逐页看** `crucible-out/preview/page-*.png`，
至少看首页、每张图所在页、每张表所在页、以及 `facts/render.json` 里
`mostly_empty` 为真的页。

脚本能算出"有效 DPI 645"，但看不出"这张架构图的箭头指错了框"、
"这个表格的最后一列被裁掉了"、"首页图和标题挤在一起"。
`crucible-out/figures/fig-NN.png` 是每张图的 300dpi 裁切，用来判断图内文字是否可读。

### 阶段 D — FAN-OUT（并行审查）

**一条消息里同时派发**下列 subagent（互相独立，无共享状态）：

| Agent | Tier | 读什么 |
|-------|------|--------|
| `crucible-build-inspector` | P0-BUILD | `render.json` `refs.json` `ingest.json` + preview PNG |
| `crucible-integrity-auditor` | P0-INTEG | `numbers.json` `tables.json` `forensics.json` + evidence dir |
| `crucible-surface-auditor` | P0-SURF | `ingest.json` 的 prose_by_section |
| `crucible-claim-auditor` | P1 | `ingest.json` `numbers.json` `tables.json` |
| `crucible-rigor-reviewer` | P2 | `tables.json` + 正文 |
| `crucible-novelty-analyst` | P3 | 正文 + WebSearch |
| `crucible-figure-critic` | P4 | `figures.json` + figures/*.png 裁切 |

每个 agent 写出 `crucible-out/candidates/<tier>.json`（finding 数组，
符合 `contracts/finding.schema.json`，但 `verdict` 留空）。

**给 agent 的 prompt 必须包含**：仓库路径、facts 目录路径、它负责的 rubric 文件路径、
输出文件路径。**不要把 facts 内容塞进 prompt** —— 让 agent 自己去读。

### 阶段 E — VERIFY（对抗验证，公理 3）

收齐候选后，对**每一条 P0 和 P1 的 finding** 派发一个 `crucible-verifier`。
verifier 的默认立场是"这条是误报"，任务是证伪。

- 证伪失败 → `verdict: CONFIRMED`
- 证伪部分成功 / 证据不足 → `verdict: PLAUSIBLE`，severity 降一级
- 证伪成功 → `verdict: REFUTED`，移出报告（保留在 findings.json 供审计）

P2–P4 的 finding 抽验即可（每类抽 2 条），P5 不验证（它本来就是预测）。

**为什么必须做**：一个乱报警的审查工具比没有工具更糟。用户会开始无视全部输出，
包括那条真正会导致 desk reject 的。已知的真实误报例子：
`\ref{box:rubric-t01}` 看起来未定义，实际由 tcolorbox 的 `label={...}` 选项定义。

### 阶段 F — PANEL（P5，审稿人模拟）

并行派发四个角色，**互相不可见，且都不给它们前面 tier 的 findings**
（否则会变成复述已知结论，失去独立信号）：

`crucible-role-ac`、`crucible-role-methodologist`、
`crucible-role-empiricist`、`crucible-role-skeptic`

产出 `crucible-out/panel/{ac,r1,r2,r3}.md` + 弱点分诊表。

### 阶段 G — VENUE（Tier V，最后）

仅当给了 `--venue`。派发 `crucible-venue-marshal` 读 `facts/venue.json`。

**先确认稿件用途**：双盲投稿版 / camera-ready / arXiv preprint。
用途不同，匿名类 finding 全部作废还是全部成立。搞错方向的误报代价极高。

### 阶段 H — FIX LOOP（最多 3 轮，公理 4）

对 `fix.kind == "mechanical"` 的 finding：

1. `crucible-fixer` 逐条应用。**每条都要先读上下文再改**。
2. 重跑 `bin/collect.py`，diff `facts/` 证明没有引入回归。
3. `crucible-fix-auditor` 逐条判定 addressed / partial / unaddressed。
4. 有 unaddressed 且轮次 < 3 则再来一轮。

对 `fix.kind == "judgment"`：产出 `crucible-out/patches/<id>.patch`，**不自动应用**。
涉及数字、主张、论证的修改由用户决定。

**机械修复的边界**（越界即降为 judgment）：
- ✅ 拼写、`\input` 路径、重复 label、缺失 `\label`、注释掉的 `\input`、数学记号
- ❌ 任何改变数值的修改
- ❌ 任何改变 claim 强度的措辞
- ❌ 删除内容以压页数（那是作者的取舍）

### 阶段 I — REPORT

调用 `crucible-report` skill 生成：

```
crucible-out/
├── REPORT.md              # 主报告：中文叙述 + 英文原文引用
├── DESK_RISK_CARD.md      # 一页纸风险卡
├── findings.json          # 全部 finding，含 REFUTED
├── ledgers/claim_ledger.md
└── patches/*.patch
```

---

## 3. 报告纪律

- **中文叙述，英文原文**。引用的稿件原文、建议的替换文本、rebuttal 措辞保持英文，
  用户要能直接粘回论文。
- **做对了的项也要写**。只列缺点的报告让作者无法判断哪些地方已经安全。
  每个 tier 都要有"已通过"小节。
- **P5 与 P0–P4 分区呈现，不混排**。事实性 finding 和主观预测放在同一个列表里，
  后者会稀释前者的可信度。
- **不给"接收概率"**。没有校准依据的精确数字，正是 CRUCIBLE 审查论文时反对的东西。
- **没有 evidence 目录时，不得断言"编造"**，只报"矛盾"。

---

## 4. 常见误报（先自查再上报）

| 现象 | 可能是合法的 |
|------|-------------|
| `\ref` 未定义 | tcolorbox / listings 用 `label={...}` 选项定义 |
| 两张表同一指标数值不同 | 协议不同（如 best-of-N vs 单次），正文若已交代则不是缺陷 |
| 某数值在表中重复出现 | 同一 baseline 在多表复用；分母相同（8/10）自然重复 |
| 摘要数字与表格不同 | 相对提升 vs 绝对值，需先复算再判断 |
| 图中红绿并存 | 若同时有形状/线型区分则可接受 |
| 机制数 ≠ ablation 行数 | 某个机制可能在另一个独立实验里单独处理了 |

判不准时，降级为 `PLAUSIBLE` 并写清"若 X 则这是缺陷，若 Y 则不是"，
让用户自己判。**不要为了报告好看而硬凑 finding。**

---

## 5. 与既有工具的关系

- 引用真实性核验复用 `citation-verify-and-fix` skill，输出并入 `findings.json`。
- 审稿人角色沿用 `role-area-chair` / `role-methodologist` /
  `role-experimentalist-reviewer` / `role-skeptic` 的 persona 结构。
- CRUCIBLE **不做**风格清洗（禁用词表、em-dash 偏好）。
  需要时用 `--style-profile <file>`，产出独立的 `STYLE.md`，不占用 severity 序列。
