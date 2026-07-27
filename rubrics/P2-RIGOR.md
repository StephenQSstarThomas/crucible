# P2-RIGOR — 实验严谨性

**判据**：实验设计本身站不站得住。即使每个数字都真实、每个 claim 都有对应实验，
实验设计有洞，结论依然不成立。

**默认 severity**：不公平比较 = `blocker`；缺失关键对照 = `major`；报告不全 = `major`。

**采集器**：`bin/tables.py` + `agent-read` + 可选 `--evidence`

---

## R1. Baseline 强度与公平性 ← 审稿人最常写的 weakness

弱 baseline 是 ML 论文被拒的头号实质原因。

| ID | 检查项 | severity |
|----|--------|----------|
| R1.1 | 包含该问题当前最强的公开方法 | blocker |
| R1.2 | baseline 与本方法用同一 backbone / 同一算力 / 同一数据 | blocker |
| R1.3 | baseline 的超参经过与本方法同等程度的调优 | major |
| R1.4 | baseline 数值来源明确（复现 or 引用原文） | major |
| R1.5 | 若复现值低于原文报告值，有解释 | blocker |
| R1.6 | 包含平凡 baseline（随机 / 多数类 / 最近邻 / 无操作） | major |
| R1.7 | 被排除的竞品有明确排除理由，且理由不是"跑不通" | major |
| R1.8 | 排除理由本身可验证（而非仅作者断言） | major |

> R1.2 在样例论文上是**做对了**的：`"All frameworks use the same LLM backbone
> (GPT-5.3-codex) and the same sandboxed execution environment with identical
> per-experiment time budgets."` CRUCIBLE 应当**明确记录做对的项**，
> 不只报缺陷——否则作者无法判断哪些地方已经安全。
>
> R1.7/R1.8 在样例论文上是**风险点**：Agent Laboratory 被排除，理由是
> "does not deliver end-to-end execution under fair-input conditions"。
> 而 Table 3 中两个 baseline 在 biology/HEP 列直接记 0 分，理由是
> "fail to install the required HEP and biology stacks"。
> 审稿人会问：**"跑不起来"记 0 分，和"不适用于该任务"记 N/A，是两件事。**
> 把对手的环境配置失败计入其平均分，再宣称自己 Overall 领先，
> 是一个会被直接攻击的设计选择。这条报 `major`，
> 修复方式是同时报告"排除失败任务后的均值"作为敏感性分析。

## R2. Ablation 完备性

（与 P1-CLAIM 的 L2 互补：L2 查"每个 claim 有没有对照"，R2 查"对照设计得对不对"）

| ID | 检查项 |
|----|--------|
| R2.1 | 每次只移除一个组件 |
| R2.2 | 移除后的系统仍是可运行的合理系统（不是故意打残） |
| R2.3 | 组件间交互有联合移除行 |
| R2.4 | ablation 覆盖全部主要 topic，而非只挑好的子集 |
| R2.5 | 超参敏感性有单独分析 |
| R2.6 | 设计空间参数（agent 数量、迭代轮数、温度）有扫描 |

## R3. 随机性与统计报告

| ID | 检查项 | severity |
|----|--------|----------|
| R3.1 | 报告了随机种子数量 / 重复次数 | major |
| R3.2 | 报告了误差棒或置信区间，并说明其含义（std / sem / CI） | major |
| R3.3 | 声称"显著"处有检验，且检验类型合适 | major |
| R3.4 | 多重比较有校正，或说明未校正 | minor |
| R3.5 | 样本量足够支撑所报精度（不要用 N=8 报三位小数） | major |
| R3.6 | 效应量与显著性同时报告 | minor |
| R3.7 | 单次运行的结果没有被当成稳定结论 | major |

> R3.5 是"一眼假"的近亲：`8/10 → 4.03`、`Accept 87.5%` 来自 `7/8`。
> N=8 的分母下报 `87.5%` 在算术上正确，但把它与 `25.0%`（2/8）并列比较、
> 并宣称 "consistently outperforms"，统计功效严重不足。
> 一个 topic 的翻转就会让 87.5% 变成 75%。这条必须报 `major`，
> 修复方式是给出 Wilson 置信区间，或明确承认样本量限制。

## R4. 选择性报告与研究者自由度

| ID | 检查项 | severity |
|----|--------|----------|
| R4.1 | best-of-N 协议被明确披露，而非隐含使用 | blocker |
| R4.2 | best-of-N 对本方法和 baseline 同等适用 | blocker |
| R4.3 | 被丢弃的运行有数量与原因说明 | major |
| R4.4 | "valid" / "completed" 的判定标准前置且统一 | major |
| R4.5 | 分母变化（8/10 vs 10/10 vs 6/10）在比较时被处理 | blocker |
| R4.6 | 指标不是事后挑出来的（预注册或多指标齐报） | major |
| R4.7 | 测试集没有被反复用于选择 | blocker |

> **R4.1 在样例论文上是做对了的**：§4.5 明确写了
> `"We therefore adopt a best-of-N protocol; Full-Auto numbers in this ablation
> reflect this setting and should be read against Table 4 rather than the
> single-run HITL results."` 披露清晰、位置正确。记为通过。
>
> **R4.5 则是严重问题**：Table 2 中各 mode 的 Valid 分母分别是
> 8/10、10/10、8/10、7/10、10/10、8/10、6/10。Mean Q 和 Accept 都是**在
> 各自不同的子集上**算的。Post-Experiment 只有 6/10 有效却报 50% accept，
> CoPilot 8/10 有效报 87.5%。**这些数字互相不可比**——分母不同意味着
> 每个 mode 面对的 topic 难度分布不同，而失败的 topic 很可能系统性地更难。
> 论文用这张表支撑"CoPilot 最优"的核心 claim。
> 这是 CRUCIBLE 在该论文上应当报出的**最严重的方法学缺陷**：`blocker`。
> 修复方式：报告在全部 mode 都成功的 topic 交集上的配对比较。
> 论文其实已经部分做了（"On matched topics, CoPilot beats Full-Auto by +3.21"），
> 但主表和摘要用的仍是不可比的边际均值。

## R5. 数据与协议

| ID | 检查项 |
|----|--------|
| R5.1 | 训练/验证/测试划分明确且无泄漏 |
| R5.2 | 数据预处理对所有方法一致 |
| R5.3 | 评测指标定义精确（含平均方式：micro/macro/加权） |
| R5.4 | 数据集版本与获取方式可追溯 |
| R5.5 | 若用 LLM 做评委，有人类一致性验证 |
| R5.6 | LLM 评委没有评价自己家族的模型（自我偏好） |
| R5.7 | 评测 prompt / rubric 公开 |

> R5.5 在样例论文上：`"Two independent agent reviewers run the strict judge in
> parallel; per-leaf disagreements exceeding |Δ| > 0.20 are re-adjudicated"`
> —— 有 agent 间一致性，但**没有 agent 与人类的一致性**。
> 整篇论文的核心指标由 LLM 评委产生，却没有证据表明该评委与人类判断对齐。
> 报 `major`。
>
> R5.6 同样命中：系统本身基于 GPT-5.3-codex，评委也是 LLM agent。
> 若评委与被评系统同源，存在自我偏好风险，需要交代。

## R6. 可复现性

| ID | 检查项 | severity |
|----|--------|----------|
| R6.1 | 代码可获取（或明确说明何时可获取） | major |
| R6.2 | 超参数完整列出 | major |
| R6.3 | 算力资源披露（GPU 型号、数量、时长） | major |
| R6.4 | 随机种子固定且公开 | minor |
| R6.5 | 依赖版本锁定 | minor |
| R6.6 | 数据获取脚本或说明 | major |
| R6.7 | 若涉及闭源 API，记录调用时的模型版本与日期 | major |

> R6.7 对 LLM 系统论文尤其关键：`GPT-5.3-codex` 会被下线或静默更新，
> 不记录调用日期意味着结果永远无法复现。
