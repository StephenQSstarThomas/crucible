# Ground Truth — 三位真实审稿人的意见（结构化）

来源：`/home/shiqiu/AutoResearchClaw/docs/reviews.md`，Submission9371。

| 审稿人 | Rating | Confidence | Quality | Clarity | Significance | Originality |
|--------|--------|-----------|---------|---------|--------------|-------------|
| 2J6J | **2 Reject** | **5 绝对确信**（"checked the math/other details carefully"） | 3 | 3 | 2 | 2 |
| 4xPF | **3 Borderline reject** | 4 | 3 | 3 | 2 | 2 |
| YvQw | **4 Borderline accept** | 3 | 3 | 3 | 3 | 3 |

**致命轴**：Significance 与 Originality（2/2/3），不是 Quality 或 Clarity（全 3）。
三人全部给 Formatting Concerns = n/a，且**无人提及匿名问题**。

---

## 去重后的 19 条独立关切

| ID | 关切 | 提出者 | 原文锚点 |
|----|------|--------|----------|
| **H01** | 正文干预次数与表格不符：表列 CoPilot=6 正文说 19；Step-by-Step=23 说 29 | 4xPF | L65 |
| **H02** | 各 mode 有效运行数不同，均值/接受率如何受影响未说明 | 4xPF, YvQw | L54, L65, L92 |
| **H03** | LLM 评委缺少与人类专家的一致性验证 | 2J6J, 4xPF, YvQw | L18, L63, L90, L99 |
| **H04** | 评委可能奖励符合本系统自身设计假设的输出（自我偏好） | 4xPF, YvQw | L54, L69, L90 |
| **H05** | 自建基准 + 自建 rubric + 自建评委的循环论证 | 2J6J, 4xPF, YvQw | L26, L52, L69, L90 |
| **H06** | baseline 太少；Claude Code / Codex / Pi 等 harness 未纳入对比 | 2J6J | L25 |
| **H07** | 新颖性是系统集成而非概念推进，未区分"新"与"实现选择" | 2J6J, 4xPF | L28, L50, L61 |
| **H08** | Table 1 能力对比表粗糙，可能夸大与相关系统的差异 | 4xPF | L50 |
| **H09** | 主张强度超出证据，需要 temper | 4xPF, YvQw | L52, L67, L92 |
| **H10** | 样本量小（25 topics / 10 topics），泛化性存疑 | 2J6J, 4xPF, YvQw | L16, L52, L92 |
| **H11** | 无显著性检验、无置信区间、无重复运行分析 | 4xPF, YvQw | L54, L92, L100 |
| **H12** | **HITL 是脚本化的，不是真人**；测的是干预时序而非人机协作 | 4xPF, YvQw | L52, L64, L90 |
| **H13** | Ablation 粒度不够：复合机制需分解（debate 分 hypothesis-only / result-only 等） | 4xPF | L62 |
| **H14** | cross-run evolution 缺少具体轨迹证据 | 4xPF | L66 |
| **H15** | 设计欠明确：SmartPause 阈值、lesson 检索机制、backbone 公平性 | YvQw | L92 |
| **H16** | Limitations 未直面影响主张的实证弱点 | 4xPF | L69 |
| **H17** | ARC-Bench 缺少硬量化指标（loss/MAE），对更低 loss 不敏感 | 2J6J | L18, L27 |
| **H18** | 基准公开发布被推迟 | YvQw | L90 |
| **H19** | best-of-3 协议 + 少 topic 使 ablation 作为机制级证据不够干净 | 4xPF, YvQw | L54, L92 |

---

## 评分口径

- **HIT** — CRUCIBLE 报出了同一条，且指向同一位置/同一论证
- **PARTIAL** — 报了相邻问题但没击中核心，或 severity 明显偏低
- **MISS** — 完全没有
- **RUBRIC-ONLY** — rubric 里有对应检查项，但本次运行未产出该 finding
- **EXTRA** — CRUCIBLE 报出而三位审稿人都没提的

**注意 H01 的分量**：4xPF 用一整条 Question 专门要求澄清这两个数字。
CRUCIBLE 把它列为 P0-INTEG-002 blocker。这是最直接的对照点。

**注意三人都没提的**：表 4 (tab:scidomain) 的 Overall 列无法复算。
2J6J 自称 confidence 5 且"仔细核对了数学"，仍未发现。
