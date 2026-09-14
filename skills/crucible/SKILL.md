---
name: crucible
description: >
  投稿前自查论文：自洽性、实验严谨性、主张与证据、引用与渲染质量，并给出按优先级排好的修改建议。
  输入一个 Overleaf 仓库（zip / git / 本地目录），多个审查 agent 并行审查：构建渲染、数据诚信、
  表层硬伤、主张-证据对齐、实验严谨性、问题定义与新颖性、呈现质量、审稿人模拟、会场符合性。
  另综合来源证据将写作方式归入人类主导、AI深度参与、全AI三档，并置于报告最前。
  每条发现可复算、可定位、经对抗验证；机械修复由 agent 执行并提交到独立分支。
  TRIGGERS — "审一下我的论文", "投稿前检查", "这篇稿子有什么问题", "review my paper
  before submission", "check this manuscript", "/crucible", 或用户给出一个论文
  仓库/zip 并要求提升质量。
  DO NOT trigger for: 写论文/生成章节（CRUCIBLE 不代写）、单纯的语法润色、已发表论文的文献综述。
argument-hint: "<paper> [--venue slug] [--purpose submission|camera-ready|preprint] [--evidence dir] [--no-fix]"
---

# CRUCIBLE

读 `CRUCIBLE.md` 了解设计公理，读 `rubrics/*.md` 了解每层的完整检查项。
本文件是**执行流程**。

本次参数：`$ARGUMENTS`

## 路径约定

`<CRUCIBLE>` 是本仓库根目录，开始时解析一次：

```bash
CRUCIBLE="${CRUCIBLE_HOME:-$(dirname "$(dirname "$(readlink -f "${CLAUDE_SKILL_DIR}")")")}"
test -f "$CRUCIBLE/bin/collect.py" && echo "$CRUCIBLE"
```

以 plugin 安装时它是 plugin 目录，用 `install.sh` 链接安装时是 clone 下来的仓库。

`<OUT>` 是本次审查的输出目录，默认 `./crucible-out`；如果它会落在稿件仓库里，改用仓库同级的
`<repo>-crucible-out`，免得被 fixer 的提交带进去。下文的 `crucible-out/...` 都指 `<OUT>/...`。

---

## 0. 五条公理（不可违反）

1. **通用性优先于会场规则** — P0–P5 与会场无关；页数/匿名/checklist 单列为 Tier V。
2. **每条发现必须可复算** — 数值类发现必须给出完整算式，不接受"看起来不对"。
3. **P0/P1/V 的每条发现必须经对抗验证** — 由独立 verifier 尝试证伪，存活才进报告。
4. **探测可用脚本，修复必须由 agent 执行** — 永远不用 `sed` 批量替换。
5. **写作来源只做三档风险判断** — 综合 provenance 与反证；文风不是检测器，不输出伪精确百分比。

---

## 1. 入参

```
/crucible <paper> [--venue <slug>] [--purpose submission|camera-ready|preprint]
                  [--evidence <dir>] [--root <main.tex>] [--tiers P0,P1,...]
                  [--no-fix] [--no-panel]
```

| 参数 | 含义 | 缺省 |
|------|------|------|
| `<paper>` | zip / git URL / 本地目录 / 单个 .tex | 必填 |
| `--venue` | 会场 profile（`venues/*.yaml`） | 不给则跳过 Tier V |
| `--purpose` | 稿件用途，决定匿名类检查是否成立 | 给了 venue 而没给时询问用户 |
| `--evidence` | 实验产物目录，启用真伪检查而非仅一致性检查 | 无 |
| `--root` | 指定主文件（仓库有多个 `\documentclass` 时） | 自动探测 |
| `--tiers` | 只跑部分 tier | 全部 |
| `--no-fix` | 只报告不修改 | 关闭（默认执行机械修复） |
| `--no-panel` | 跳过审稿人模拟 | 关闭 |

---

## 2. 阶段

```
A INGEST → B COLLECT → C PREVIEW
  → D REVIEW   并行波 1：tier 审查 + 审稿人模拟 + 会场
  → E VERIFY   并行波 2：每条候选一个 verifier
  → F FIX      串行，最多 3 轮
  → G SYNTHESIZE 并行波 3：写作来源 + 修改建议
  → H REPORT
```

**需要问用户的事都在阶段 A 问完。** 后面的并行波一旦派发就不应再停下来等人。

### 阶段 A — INGEST

1. 解包/克隆到工作目录。zip 用 `unzip -q`；git 用 `git clone --depth 1`。
2. 若是用户的真实 Overleaf 仓库，**先建 `crucible/fixes` 分支**（阶段 F 要用）。
   非 git 目录则 `git init` 后提交一次基线，保证修改可回滚。
3. 以下情况**先问用户，得到回答再继续**：
   - 仓库里有多个 `\documentclass` 文件，或给了 `--venue` 但主文件没用该会场的 style：
     投的是哪一个？审错文件的整份报告都是废的。
   - 给了 `--venue` 但没给 `--purpose`：这是双盲投稿版、camera-ready 还是 preprint？

### 阶段 B — COLLECT（确定性）

```bash
python3 <CRUCIBLE>/bin/collect.py <repo> -o <OUT> \
    [--venue <slug>] [--evidence <dir>] [--root <main.tex>] \
    [--double-blind yes|no]      # purpose=submission → yes，其余 → no
```

产出 `facts/*.json` + `preview/page-NN.png` + `figures/fig-NN.png`。

**编译失败时不要继续。** 后面每一层都依赖渲染出的 PDF。
把编译错误作为唯一的 P0-BUILD blocker 报出来，请用户决定。

读 `facts/_summary.json` 建立全局印象。**不要把所有 facts JSON 一次性读进上下文** ——
`numbers.json` 可能上万行，用 `python3 -c` 或 `jq` 只取需要的字段。

### 阶段 C — 看预览

**这一步不能跳过。** 逐页看 `preview/page-*.png`，至少看首页、每张图和表所在页、
以及 `facts/render.json` 里 `mostly_empty` 为真的页。

脚本能算出"有效 DPI 645"，但看不出"箭头指错了框"、"表格最后一列被裁掉了"。
把看到的肉眼问题记成一段笔记，放进阶段 D 派给 build inspector 和 figure critic 的 prompt。

### 阶段 D — REVIEW（并行波 1）

**在同一条消息里发出下列全部 Agent 调用（`subagent_type` 用表中名字），全部返回后再进入阶段 E。**
它们之间没有依赖，也不共享输出文件。

以 plugin 安装时 agent 名带命名空间，如 `crucible:crucible-verifier`；用 `install.sh`
安装时不带。以当前会话里可用的 agent 列表为准。

| Agent | Tier | 读什么 | 写到 |
|-------|------|--------|------|
| `crucible-build-inspector` | P0-BUILD | `render.json` `refs.json` `ingest.json` + preview | `candidates/P0-BUILD.json` |
| `crucible-integrity-auditor` | P0-INTEG | `numbers.json` `tables.json` `forensics.json` `refs.json` + evidence | `candidates/P0-INTEG.json` |
| `crucible-surface-auditor` | P0-SURF | `ingest.json` 的 prose_by_section | `candidates/P0-SURF.json` |
| `crucible-claim-auditor` | P1 | `ingest.json` `numbers.json` `tables.json` | `candidates/P1-CLAIM.json` + `ledgers/claim_ledger.md` |
| `crucible-rigor-reviewer` | P2 | `tables.json` + 正文 | `candidates/P2-RIGOR.json` |
| `crucible-novelty-analyst` | P3 | 正文 + 联网检索 | `candidates/P3-DEF.json` |
| `crucible-figure-critic` | P4 | `figures.json` + figures 裁切 | `candidates/P4-PRES.json` |
| `crucible-role-ac` | P5 | 论文本体 | `panel/ac.md` |
| `crucible-role-methodologist` | P5 | 论文本体 | `panel/r1.md` |
| `crucible-role-empiricist` | P5 | 论文本体 | `panel/r2.md` |
| `crucible-role-skeptic` | P5 | 论文本体 | `panel/r3.md` |
| `crucible-venue-marshal` | V | `venue.json` + venue yaml | `candidates/V-VENUE.json` + `DESK_RISK_CARD.md` |

- `--tiers` 限定时只派对应的 agent；`--no-panel` 时不派四个角色；没给 `--venue` 时不派会场。
- 四个审稿角色**不给任何 findings**，互相不可见。它们与 tier 审查同批跑，正是因为不依赖前者。
- Claude Code 默认同时最多 20 个 subagent（`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`），本波最多 12 个加分片，
  一般不需要分批；超出时分批，批内并行，批间按表中顺序。

**长稿分片。** `facts/ingest.json` 的 `n_lines` 超过 1500 时，把 surface auditor 和
claim auditor 按章节切成若干片并行（每片约 800 行，章节不拆开）。第 k 片（从 0 起）
写 `candidates/<TIER>.part-k.json`，id 编号从 `k*100+1` 开始，保证各片 id 不冲突。
claim auditor 分片时，各片把账本写到 `ledgers/claim_ledger.part-k.md`，由编排器合并成
`ledgers/claim_ledger.md` 并统一重新编号 C01、C02…。

**派发 prompt 模板**（每个 agent 一份，不要把 facts 内容塞进 prompt）：

```
CRUCIBLE 根目录: <CRUCIBLE>      （rubrics/ contracts/ bin/ 相对此目录）
稿件仓库: <repo>   主文件: <root.tex>
输出目录: <OUT>                  （crucible-out/... 相对此目录）
负责的 rubric: <CRUCIBLE>/rubrics/<TIER>.md
输出文件: <OUT>/candidates/<TIER>.json
稿件用途: <submission|camera-ready|preprint|未指定>   证据目录: <dir|无>
预览笔记: <阶段 C 的笔记，只给 build inspector / figure critic>
分片: <第 k 片，章节范围，id 从 k*100+1 起 | 不分片>
```

### 阶段 E — VERIFY（并行波 2，公理 3）

1. 验证范围：
   - P0 与 P1、V 的**每一条**候选；
   - P2–P4 每个 tier 抽 2 条（优先 severity 最高的）；**抽验中有任何一条 REFUTED，
     该 tier 其余条目全部验证**；
   - P5 不验证，它本来就是预测。
2. 每条候选派发一个 `crucible-verifier`，prompt 里给 finding 全文、仓库路径、`<OUT>`。
   **在同一条消息里发出多个 Agent 调用**，每批不超过 15 个，一批全部返回再发下一批。每个 verifier 只写
   `verdicts/<finding-id>.json`，不改 candidates。
3. 全部完成后合并：

```bash
python3 <CRUCIBLE>/bin/merge_findings.py <OUT>
```

它检查 finding 契约、挂上 verdict、把 `PLAUSIBLE` 降一级 severity、排序，写出
`findings.json` 与 `finding_counts.json`。P0/P1/V 缺 verdict 会报错退出 —— 补派 verifier 后重跑。

判定含义：证伪失败 → `CONFIRMED`；证据不足或依赖判断 → `PLAUSIBLE`；证伪成功 → `REFUTED`
（只留在 findings.json 供审计，不进报告和修改建议）。

**为什么必须做**：一个乱报警的审查工具比没有工具更糟。已知的真实误报：
`\ref{box:rubric-t01}` 看起来未定义，实际由 tcolorbox 的 `label={...}` 选项定义。

### 阶段 F — FIX LOOP（串行，最多 3 轮，公理 4）

`--no-fix` 时跳过。修复会改动稿件，**不能并行**。

对 `fix.kind == "mechanical"` 且未被 REFUTED 的 finding：

1. `crucible-fixer` 逐条应用，每条先读上下文再改，写 `fixes/round-N.json`。
2. 重跑 `bin/collect.py`，diff `facts/` 证明没有引入回归。
3. `crucible-fix-auditor` 逐条判定，写 `fixes/audit-round-N.json`。
4. 有 unaddressed 且轮次 < 3 则再来一轮。
5. 结束后重跑 `bin/merge_findings.py`，把审计通过的修复标为 `auto_applied`。

对 `fix.kind == "judgment"`：fixer 只产出 `patches/<id>.patch`，**不自动应用**。

**机械修复的边界**（越界即降为 judgment）：
- ✅ 拼写、`\input` 路径、重复 label、缺失 `\label`、注释掉的 `\input`、数学记号
- ❌ 任何改变数值的修改
- ❌ 任何改变 claim 强度的措辞
- ❌ 删除内容以压页数（那是作者的取舍）

### 阶段 G — SYNTHESIZE（并行波 3）

**在同一条消息里发出这两个 Agent 调用：**

- `crucible-authorship-assessor`：读 `rubrics/A-AUTHORSHIP.md`、`facts/authorship.json`、源码和
  `findings.json`（只用非 REFUTED 项），写 `authorship_assessment.json`。只选 `人类主导`、
  `AI深度参与`、`全AI` 之一；不输出百分比，不凭 stylometry 升档。
- `crucible-revision-planner`：读 `findings.json`、`fixes/`、`patches/`、`ledgers/claim_ledger.md`、
  `panel/*.md`，写 `REVISION_PLAN.md` —— 按先后顺序排好的修改清单，每条带位置、
  英文替换文本、连带位置、工作量、改完怎么确认。审稿人模拟来源的条目单独成节并标注"预测，非事实"。

### 阶段 H — REPORT

调用 `crucible-report` skill 生成 `REPORT.md` 与 `DESK_RISK_CARD.md`，然后运行：

```bash
python3 <CRUCIBLE>/bin/validate_report.py <OUT>
```

校验失败说明产物不完整，修正后重跑，不要把未通过校验的报告交给用户。

最后在对话里给用户一段简短总结：几条 blocker / major、最该先改的三件事（取自
REVISION_PLAN.md 的"先做这些"）、机械修复落在哪个分支、报告路径。

```
<OUT>/
├── REPORT.md                  主报告
├── REVISION_PLAN.md           修改建议（按先后顺序）
├── DESK_RISK_CARD.md          一页纸风险卡
├── authorship_assessment.json 三档写作来源判断
├── findings.json              全部 finding，含 REFUTED
├── finding_counts.json        报告摘要表的数字来源
├── candidates/ verdicts/      并行审查与验证的原始输出
├── ledgers/claim_ledger.md
├── panel/                     四份模拟审稿意见
├── fixes/ patches/
└── facts/ preview/ figures/
```

---

## 3. 报告纪律

- **中文叙述，英文原文**。引用的稿件原文、建议的替换文本、rebuttal 措辞保持英文，
  用户要能直接粘回论文。
- **做对了的项也要写**。每个 tier 都要有"已通过"小节。
- **P5 与 P0–P4 分区呈现，不混排**。
- **三档写作来源判断放在 REPORT.md 标题后的第一节**，并明确不是取证结论。
- **不给"接收概率"**。
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

## 5. 范围

- 引用真实性核验：环境里有引用核验类 skill 时可以复用，结果按 finding 格式并入 `candidates/P0-INTEG.json`；
  没有就由 integrity auditor 联网抽查。
- CRUCIBLE **不做**风格清洗（禁用词表、em-dash 偏好），不代写新实验、新章节、新 claim。
