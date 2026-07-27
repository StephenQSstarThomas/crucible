# 验证：CRUCIBLE vs 三位真实审稿人

同一篇稿子（Submission9371 / AutoResearchClaw），拿真实评审当 ground truth。

| 审稿人 | Rating | Confidence | Significance | Originality |
|--------|--------|-----------|--------------|-------------|
| 2J6J | 2 Reject | **5**（"checked the math/other details carefully"） | 2 | 2 |
| 4xPF | 3 Borderline reject | 4 | 2 | 2 |
| YvQw | 4 Borderline accept | 3 | 3 | 3 |

Quality 与 Clarity 三人全给 3；被拒的轴是 **Significance / Originality**。

---

## 方法：盲测，以及必须声明的污染

三个 agent（P1-CLAIM / P2-RIGOR / P3-DEF）在**未接触 `reviews.md`** 的前提下独立审查，
只给论文与 `facts/`。之后再与人类意见对照。

**污染声明**——我在写派发 prompt 时**已经读过审稿意见**，因此有两处提示带了先验：

| 被污染项 | 我在 prompt 里写了什么 | 影响 |
|---------|---------------------|------|
| H12 构念效度 | 明写"论文声称的构念（**如 human-AI collaboration**）与实际测量是否一致" | `P1-CLAIM-003` **不计为独立发现** |
| H08 能力对比表 | 明写"related_work.tex 里有一张 capability matrix，按 D3.7 逐格联网核实" | `P3-DEF-010` 计为**半独立**（D3.7 在读评审前就已写入 rubric，但我做了指向） |

其余 17 项无提示。下表按此口径计分。

---

## 覆盖度：19 条人类关切

| ID | 人类关切 | CRUCIBLE | 判定 |
|----|---------|----------|------|
| H01 | 干预次数 19/29 vs 表 6/23 | `P1-CLAIM-001` blocker | ✅ 独立命中 |
| H02 | 各 mode 有效运行数不同 | `P2-RIGOR-001` blocker | ✅ 独立命中 |
| H03 | LLM 评委缺人类一致性 | `P2-RIGOR-011` major | ✅ 独立命中 |
| H04 | 评委奖励本系统自身设计 | `P2-RIGOR-004` blocker | ✅ **更锐利** |
| H05 | 自建基准循环性 | `P2-RIGOR-003/004` blocker | ✅ **更锐利** |
| H06 | baseline 太少（Claude Code/Codex/Pi） | `P2-RIGOR-012`（缺无脚手架对照）+ `P3-DEF-011`（AIDE 不在 Table 1） | ⚠️ 部分 |
| H07 | 新颖性只是集成 | `P3-DEF-007`（MetaClaw 零引用） | ✅ **更锐利** |
| H08 | Table 1 粗糙、夸大差异 | `P3-DEF-010` blocker（5 格与一手资料矛盾） | ✅ 半独立·更锐利 |
| H09 | 主张过强需 temper | `P1-CLAIM-005/007/011/013` | ✅ 独立命中 |
| H10 | 样本量小 | `P2-RIGOR-008`（Wilson 区间 45–63pp） | ✅ **更锐利** |
| H11 | 无显著性检验/CI | `P2-RIGOR-007/009` | ✅ 独立命中 |
| H12 | 脚本化 HITL ≠ 人机协作 | `P1-CLAIM-003` blocker | 🟡 **被我提示，不计独立** |
| H13 | ablation 粒度（复合机制未分解） | — | ❌ **漏报** |
| H14 | cross-run evolution 缺轨迹 | `P1-CLAIM-007` | ✅ 独立命中 |
| H15 | SmartPause / backbone 公平性欠明确 | `P1-CLAIM-010` + `P1-CLAIM-004` | ✅ **更锐利** |
| H16 | limitations 不充分 | `P1-CLAIM-014`（并给出取消注释的具体行号） | ✅ **更锐利** |
| H17 | rubric 对更低 loss/MAE 不敏感 | — | ❌ **漏报** |
| H18 | 基准发布被推迟 | — | ❌ **漏报** |
| H19 | best-of-3 使 ablation 不干净 | `P2-RIGOR-010`（主表根本未披露重复次数） | ✅ **更锐利** |

**13 条独立命中 · 1 条半独立 · 1 条被提示 · 1 条部分 · 3 条漏报。**
独立覆盖率 13/19 = **68%**；含半独立与部分为 15/19 = **79%**。

其中 8 条比人类**更锐利**：不只指出"有问题"，还反解出参数、算出区间、定位到行号。

---

## CRUCIBLE 查到而三位审稿人都没查到的

2J6J 自称 confidence 5 且"仔细核对了数学"。以下均未出现在任何一份意见里。

### 1. 表 3 的聚合口径被反解出来，与 caption 声明不符

caption 写 `biology B01–B07 (7) / statistics S01–S03 (3) / HEP P01–P10 (10)，N=20`。
穷举 0–20 三维整数权重，能**同时**拟合三行的口径**唯一**（比例 7:2:1）：

```
                   印出    caption口径(7:3:10,N=20)   实际口径(7:2:1,N=10)
AutoResearchClaw   0.867        0.6984  ✗                0.8669  ✓
AIDE-ML            0.090        0.0678  ✗                0.0904  ✓
AI Scientist v2    0.084        0.0627  ✗                0.0836  ✓
```

**HEP 是本方法得分最低（0.489）、caption 里任务最多（10）的一列，实际权重是 1；
biology 得分最高（0.912），权重保持 7。**

### 2. "super-additively" 被论文自己的数据反证

```
单独移除 debate        损失 5.62 − 4.25 = 1.37
单独移除 self-healing  损失 5.62 − 4.83 = 0.79
若可加，联合移除应为   5.62 − 1.37 − 0.79 = 3.46
实测联合移除                              = 3.47   （差 0.01）
```

Quality 维度上**恰好可加**，不支持 super-additive。只有 completion 维度真超可加。
而结论段用的是 "confirms"。

### 3. 54.7% 拿"有人干预"对比"全自动"

摘要不加限定地用 CoPilot（有人介入）对比 AI Scientist v2（全自动）。
同自主度的对比是 Full-Auto 0.596 vs 0.419 = **42.2%**。两个都报反而更可信。

### 4. 竞品能力被错误陈述，且主结果的因果解释建立在其上

Table 1 给 AI Sci v2 的 Self-healing = ✗。但其出厂配置 `bfts_config.yaml` 含
`max_debug_depth: 3`、`debug_prob: 0.5`（本次独立 WebFetch 核实）。
§4.2 又把 CE 差距归因于 "AIDE-ML's ... lack of self-healing"，而 AIDE 的三个核心算子
就是 draft / **debug** / improve。**AIDE-ML 是仅有的两个实测基线之一，却不在 Table 1 里。**

### 5. 最近的前作躺在 .bib 里，零引用

| bib key | 在 bib | 正文引用次数 |
|---------|-------|------------|
| `xia2026metaclaw` | ✓ | **0** |
| `liu2026simplemem` | ✓ | **0** |
| `trehan2026whyllm` | ✓ | **0** |

MetaClaw 与本文同一 GitHub org、作者高度重叠、机制是"从失败中蒸馏技能并注入"，
且其实验就跑在 AutoResearchClaw 上。"这是 MetaClaw 换了个调度器"目前没有反驳材料。
`trehan2026whyllm` 是反向证据（LLM 尚不能做科学家）。

### 6. 附录里 11 个段落被注释掉，491 词

包括作者自己写下的评委风格偏置（正是 H04）、本系统数值验证在 T09/T25 失效、
评委输入截断与"results-only 不读代码"、以及审稿人索要的 per-topic 表。
**这是"补写 limitations"与"取消 appendix.tex:396–406 注释"的区别。**

### 7. 干预可能直接作用在评分器上

```
appendix.tex:46    20 & Quality_Gate & quality_report.json & HITL Gate
appendix.tex:687   "Stage-20 score: 4.0."      :690   "Stage-20 score: 8.0."
```

端到端 1–10 分**就是 Stage-20 Quality Gate 打的分**，而 Stage 20 同时是一个 HITL 介入点。
按 `tab:mode-mapping` 分组：

| 在 Stage 20 介入 | Mean Q |
|---|---|
| Gate-Only(5,9,**20**) / CoPilot(…,**20**) / Step-by-Step(全 23) / Post-Experiment(14,17,**20**) | 5.03 / 7.27 / 5.19 / 5.08 |
| Full-Auto(none) / Pre-Experiment(5,8,9) | 4.03 / 4.28 |

**两组完全不重叠。** 把归属存疑的 Thorough（"phase boundaries"）划到未介入组，
min 5.03 > max 4.86，结论不变。

论文的核心 claim 是"在高杠杆决策点的定向干预优于全自动与逐步监督"。
若评分器本身就是被干预的那个阶段，这个 claim 就有一条未被排除的平凡解释。
**这是唯一能一句话击穿标题里 "Human-AI Collaboration" 的点，三位审稿人无人提及。**

### 8. 基准 rubric 把本系统的内部路径写进了给分条件

`appendix.tex:552–553`，公布的 T01 rubric：

> Machine-readable artifact (`results/metrics.json` or **`stage-14/experiment_summary.json`**)
> with numeric accuracy *and* …

`stage-14/` 是 AutoResearchClaw 自己的阶段编号。该叶子权重 16.67，占 CE 的 2/3，
对 Overall 的最大影响 0.25 × 0.667 = **0.167**，
大于 CoPilot 对 AIDE-ML 的全部优势（0.648 − 0.511 = **0.137**）。

这是 H04/H05 的最锐利形式：不是"评委可能偏好本系统的风格"，
而是**评分标准里直接写着本系统的产物路径**。

### 9. 其他

- `w/o Verification` 的 Quality 只在 completed topic 上取均值，补齐后"debate 是最大质量贡献者"可能反转
- 端到端 1–10 分疑似由系统自身 Stage-20 Quality Gate 产生，而七个 mode 中四个恰在 Stage 20 介入
- rubric 直接以本系统内部产物路径 `stage-14/experiment_summary.json` 作为给分条件
- 摘要承诺 "prevents hallucinated citations"，全文无任何引用验证的测量
- "without per-domain engineering effort" 与前两句自述的三套人工领域技能包矛盾
- "the only mode achieving 10/10 validity" 是错的，Step-by-Step 也是 10/10
- 案例研究图内嵌截图在最终尺寸约 1.2pt（有效 DPI 761，通过 DPI 检查）

---

## CRUCIBLE 的失误与已做的修正

诚实记录，不修饰。

| 失误 | 性质 | 修正 |
|------|------|------|
| 首轮断言"没有 agent 与人类的一致性验证" | **事实错误**。`appendix.tex:510` 确有 `Mean per-leaf \|Δ\| < 0.10` | 真实缺陷是它埋在附录、无 N、无统计量、正文未提。已改为 `P2-RIGOR-011` |
| best-of-N 判为「通过」 | **校准错误**。披露正确，但两位审稿人仍扣分 | `R4.1` 拆成两问：披露了吗 / 披露后还撑得起 claim 吗 |
| H13 ablation 粒度漏报 | rubric 缺项 | 新增 `R2.7` |
| H17 指标不奖励"更好"漏报 | rubric 缺项 | 新增 `R5.9` |
| H18 基准发布推迟漏报 | rubric 缺项 | 仍缺，待补 |
| Tier V 五条 desk-reject | 三位审稿人均报 Formatting = n/a | **假设错误而非检查错误**：报告开头已声明"按双盲投稿版审查，若为 camera-ready 则全部作废"。zip 日期晚于评审，是评审后的修订版，故这些结论指向**重投**而非已投版本 |

最后一行是公理 1 在起作用：会场规则独立成层，假设一旦推翻，只有该层作废，
P0–P5 的 40 余条结论全部不受影响。

---

## 结论

- 真实审稿人的 19 条关切，CRUCIBLE 独立命中 13 条（68%），其中 8 条给出了比人类更精确的定位与算式。
- 3 条漏报已转化为 rubric 新检查项（`R2.7` / `R5.9` / 待补）。
- CRUCIBLE 另外查出 15+ 条三位审稿人都没查到的问题，其中至少 4 条（表 3 口径、
  super-additive 反证、54.7% 口径、竞品能力误标）属于会直接动摇主结果的量级。
- 两类工作**互补而非替代**：人类擅长判断"这个贡献够不够"（Significance / Originality
  正是三人一致压分的轴，也是 CRUCIBLE 明确不做判断的地方）；
  CRUCIBLE 擅长"把每个数字算一遍、把每条断言核一遍、把源码里藏着的东西翻出来"。
