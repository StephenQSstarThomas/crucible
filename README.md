# CRUCIBLE

**投稿前的论文审查与提升系统。skills + subagent 驱动。**

> 坩埚。矿石入炉，贱金属化为炉渣被烧掉，剩下的才是可发表的东西。

输入一个 Overleaf 仓库，输出一份按严重级别排序、每条可复算、经对抗验证的缺陷清单，
以及 agent 执行的修复。

---

## 装

```bash
git clone <this-repo> ~/crucible
cd ~/crucible && ./install.sh
```

依赖：`python3`、`tectonic`、`pymupdf`、`pillow`、`pyyaml`。
没有 `tectonic` 也能跑源码层检查，但所有基于渲染结果的检查会被跳过 ——
而那恰好是最重要的一部分（见下）。

## 用

```
/crucible <paper> [--venue neurips-2026] [--evidence <dir>] [--no-fix]
```

`<paper>` 可以是 zip、git URL、本地目录，或单个 `.tex`。

```bash
/crucible ~/AutoClaw_for_NIPS.zip --venue neurips-2026
/crucible ~/paper --evidence ~/paper/runs      # 启用真伪检查
/crucible ~/paper --no-fix                     # 只报告，不碰 .tex
```

也可以只跑确定性采集，不用 agent：

```bash
python3 bin/collect.py ~/paper -o crucible-out --venue neurips-2026
```

---

## 为什么不是又一个 latex linter

因为 linter 查的是源码，审稿人看的是 PDF。

这个仓库最初是为了审一篇真实的 NeurIPS 投稿而写的。那篇稿子已经过了
6 轮人工润色，润色报告显示"所有静态检查为空"。CRUCIBLE 在它上面找到的东西包括：

- `checklist.tex` 存在、5345 字节、**已完整填写**，但 `main.tex` 里
  `\input{checklist}` 被注释掉了。扫源码目录的检查会认为 checklist 存在。
  NeurIPS 对缺 checklist 的稿子直接 desk reject。
- 正文写 "CoPilot ... with **19** targeted interventions"，
  它引用的那张表里写的是 **6**。同段的 **29** 在论文任何表格中都不存在。
- 某张表的 `Overall` 列，用 caption 声明的权重怎么算都得不到印出来的数
  （反解发现它实际按 4 个任务算，caption 写的是 3 个）。
- 仓库里的 `POLISH_REPORT.md` 还在引用上一版的 headline 数字。
- 一个被 `\input` 的 section 文件只剩两行注释。

这些都不是风格问题，也没有一个能靠查禁用词表发现。

---

## 四条设计公理

### 1. 通用性优先于会场规则

会场规则每年都变，正确性不变。所以 P0 只包含"在任何会场任何年份都是错的"东西。
页数、匿名、checklist 这些**放在最后单独一轮 (Tier V)**。
改投另一个会场时，P0–P5 的结论全部复用。

### 2. 每条发现必须可复算

不接受"看起来不对"。数值类发现必须给出完整算式，并把所有替代算法都试一遍。
最好能**反解出作者实际用的参数**，把"某处有错"变成"caption 与计算不一致，改哪个由你定"。

### 3. 每条 P0/P1 发现必须经对抗验证

由一个独立的 verifier 尝试**证伪**，默认立场是"这条是误报"。存活才进报告。

一个乱报警的审查工具比没有工具更糟：用户会开始无视全部输出，
包括那条真正会导致 desk reject 的。

### 4. 探测可用脚本，修复必须由 agent 执行

`bin/` 只采集事实，不下判断。判断和修复都由 subagent 做。
永远不用 `sed` 批量替换 —— 它会把 `generatio` 改对，同时改掉某个作者姓氏
和某段 verbatim 里的字符串。

---

## 严重级别阶梯

| Tier | | 通用? |
|------|---|-------|
| **P0-BUILD** | 构建与渲染：编译、`??`、缺图、草稿残留、空的被引文件 | ✅ |
| **P0-INTEG** | 数据与引用诚信：数值矛盾、表内算术、过期数字、幻觉引用、图像复用 | ✅ |
| **P0-SURF** | 表层硬伤：错别字、记号、结构完整性 | ✅ |
| **P1-CLAIM** | 主张—证据对齐；**每个声称的机制必须有自己的对照** | ✅ |
| **P2-RIGOR** | 实验严谨性：baseline、ablation、误差棒、选择性报告、分母可比性 | ✅ |
| **P3-DEF** | 问题定义 → 新颖性 | ✅ |
| **P4-PRES** | 呈现质量：**最终渲染尺寸下的**图表可读性 | ✅ |
| **P5-PANEL** | 审稿人模拟与 rebuttal 就绪度 | ✅ |
| **V-VENUE** | 会场符合性 | ⚠️ 最后单独跑 |

完整检查项在 `rubrics/`，每层一个文件。

### 关于 P3：为什么叫「问题定义」而不是「新颖性」

Novelty 争议几乎从不是"这个想法有没有人做过"的事实之争，而是**定义之争**。
审稿人说"这就是 X 的变体"，作者说"不是，我们解决的是 Y" —— 双方在谈不同的问题，
因为论文从未把问题形式化地钉死。

所以 P3 的第一个检查项不是搜前作，而是：**能不能用一句话说清
`Given ___, produce ___, subject to ___, measured by ___`？**
说不清，novelty 就无法辩护，无论实验多好。

---

## 结构

```
CRUCIBLE.md              设计公理与架构
rubrics/                 九个 tier 的完整检查项 —— 系统的知识都在这里
contracts/               finding.schema.json
bin/                     确定性采集器（只出事实，不下判断）
  collect.py               一次跑完全部
  ingest.py                \input 树、章节、浮动体、宏、行号映射
  render.py                tectonic 编译、日志解析、逐页 PNG、PDF 文本层
  tables.py                LaTeX tabular → 可寻址网格（表内算术复算的基础）
  numbers.py               数值账本 + 锚定检查（正文数字 vs 它引用的表）
  refs.py                  引用/标签/图片 双向差集
  figures.py               版面实测 DPI、色盲模拟、感知哈希查重、300dpi 裁切
  forensics.py             末位数字、Benford、重复行、小分母 —— 红旗非证据
  venue.py                 页数、样式篡改、匿名、必需材料
skills/
  crucible/                编排：INGEST→COLLECT→看预览→FAN-OUT→VERIFY→PANEL→VENUE→FIX→REPORT
  crucible-report/         报告渲染规范
agents/                  15 个 subagent
venues/                  会场规则数据（带 verified_on 时效字段）
```

## 输出

```
crucible-out/
├── REPORT.md              主报告（中文叙述 + 英文原文）
├── DESK_RISK_CARD.md      一页纸：会不会当场被拒
├── findings.json          结构化，含被证伪的条目供审计
├── facts/                 确定性采集结果，可 diff、可 CI
├── preview/page-NN.png    逐页渲染图
├── figures/fig-NN.png     每张图 300dpi 裁切
├── ledgers/claim_ledger.md
├── patches/               需人工批准的修改
└── panel/                 四份模拟审稿意见
```

机械修复直接提交到 `crucible/fixes` 分支，可 `git diff` 可 `git revert`。

---

## 不做的事

- **不代写论文。** 不生成新实验、新章节、新 claim。
- **不做风格清洗。** 禁用词表、em-dash 偏好默认不产生 finding。
  需要时用 `--style-profile`，产出独立文件，不占 severity 序列。
- **不判断科学价值。** 不会说"这个方向没意思"。
- **不给接收概率。** 没有校准依据的精确数字，正是它审查论文时反对的东西。
- **无 `--evidence` 时不指控造假**，只报矛盾。
  说两个数不一致是事实陈述；说一个数是编的是指控，需要证据。
