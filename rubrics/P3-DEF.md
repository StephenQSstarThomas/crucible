# P3-DEF — 问题定义与新颖性

**判据**：这篇论文到底在解决什么问题，说清楚了没有；说清楚之后，
它相对最近的前作到底多做了什么。

用户的洞见，本 tier 的立论基础：
> "novelty问题，其实本质是来自于定义的问题是否清晰"

**默认 severity**：问题定义缺失 = `blocker`；贡献增量不可辩护 = `major`。

**采集器**：`agent-read` + 网络检索

---

## 为什么先查定义，再查新颖性

Novelty 争议在 rebuttal 里几乎永远是这个形状：

> **R2**: This is essentially [prior work] with a different scheduler.
> **Authors**: We respectfully disagree. [Prior work] addresses X, whereas we address Y.

双方都没错，因为论文从未把问题**形式化地钉死**。审稿人按自己的理解归类，
作者按自己的理解辩护，两边谈的不是同一个问题。

**如果论文能用一句话说清输入、输出、约束和成功判据，
"这是 X 的变体吗"就变成一个可以被事实回答的问题。** 说不清，
novelty 就永远无法辩护，无论实验多好。

所以本 tier 的顺序不可颠倒：D1 不过，D2/D3 的结论都不作数。

---

## D1. 问题定义的锐利度

| ID | 检查项 | severity |
|----|--------|----------|
| D1.1 | 存在一处明确的问题陈述（不是散落在引言各段） | blocker |
| D1.2 | 输入是什么，说清楚了 | blocker |
| D1.3 | 输出是什么，说清楚了 | blocker |
| D1.4 | 约束条件是什么（算力/数据/时间/可观测性） | major |
| D1.5 | 成功的判据是什么，且可度量 | blocker |
| D1.6 | 问题的边界清楚（什么**不**在范围内） | major |
| D1.7 | 若引入新术语/新任务，有形式化定义而非仅举例 | major |
| D1.8 | 定义在全文保持不变（不中途悄悄换） | blocker |

**D1 的检验方式**：CRUCIBLE 要求 agent 只读引言，
写出一句 `Given ___, produce ___, subject to ___, measured by ___`。
写不出来，或需要读到第 4 节才能补全，即为 D1 失败。

> 在样例论文上做这个检验：
> `Given a research topic, produce a completed experiment (and optionally a paper),
> subject to a fixed LLM backbone and time budget, measured by an LLM judge's
> CD/CE/RA rubric score.`
>
> 前三项能从引言写出。**第四项不能**——评分判据（CD:CE:RA = 25:25:50）
> 直到 §4.1 才出现，且权重的选择理由（"RA receives double weight because..."）
> 是事后论证。当核心指标的定义出现在实验节而非问题陈述中时，
> 审稿人会怀疑指标是为结果服务的。报 `major`，
> 修复方式是把评价判据前移到引言并给出独立于结果的理由。

## D2. 贡献增量

| ID | 检查项 | severity |
|----|--------|----------|
| D2.1 | 最近的前作被明确点名 | blocker |
| D2.2 | 相对该前作的差异被具体描述（不是"我们更好"） | blocker |
| D2.3 | 该差异有对应的实验证据 | major |
| D2.4 | 差异是概念性的，不只是工程量堆叠 | major |
| D2.5 | 若为多个已有技术的组合，说明组合本身的非平凡性 | major |
| D2.6 | 贡献列表中每一条都是本文做的（不含前作已有的） | blocker |
| D2.7 | 不声称 "first" 除非有系统性检索支撑 | major |

> D2.6 命中风险：论文写 `"The HEP agent is equipped with the FeynRules,
> MadGraph, and MadAnalysis skills drawn from [qiu2026...], which introduced
> the ColliderAgent architecture we directly adopt here"`。
> **诚实地承认了直接采用前作架构**——这很好。但摘要与贡献列表中
> "cross-domain coverage" 被列为本文成果之一。
> 审稿人会问：跨域能力有多少来自本文，多少来自被采用的 ColliderAgent？
> 报 `major`，修复方式是在贡献列表中标注该项的边界。
>
> 另注：`qiu2026` 与本文作者列表中的 `Shi Qiu` 同名——这是自引，
> 在双盲评审下另有风险，交由 V-VENUE 处理。

## D3. 相关工作覆盖

| ID | 检查项 | severity |
|----|--------|----------|
| D3.1 | 覆盖了该问题下审稿人会立刻想到的方法 | major |
| D3.2 | 覆盖了近 12 个月的工作 | major |
| D3.3 | 相关工作按**论点**组织，而非按时间流水账 | minor |
| D3.4 | 每条相关工作说明了与本文的关系，而非仅摘要 | minor |
| D3.5 | 没有为凑数而引用不相关文献 | minor |
| D3.6 | 没有系统性忽略与本文结论相反的工作 | blocker |
| D3.7 | 竞品的能力描述准确（对比表中的 ✓/✗ 经过核实） | blocker |

> D3.7 是对比表（capability matrix）的固有风险：论文用 ✓/✗/~ 三档描述
> 竞品是否具备某能力。**这些标记是关于他人系统的事实断言**，
> 标错就是错误陈述他人工作。CRUCIBLE 在授权联网时会逐格核对竞品文档。
> 这类 finding 的 severity 是 `blocker`，因为被误标的作者很可能就是审稿人。

## D4. 定位与叙事

| ID | 检查项 |
|----|--------|
| D4.1 | 论文类型自我定位清楚（新方法 / 新benchmark / 实证研究 / 系统论文） |
| D4.2 | 评价方式与论文类型匹配（系统论文不必刷 SOTA，但需可用性证据） |
| D4.3 | 动机段落描述的问题，确实是实验所解决的问题 |
| D4.4 | 引言承诺的 "we show that ..." 在实验节逐条兑现 |
| D4.5 | 没有把工程完成度当成科学贡献 |

> D4.1/D4.2 对该样例尤其重要：这是一篇**系统 + benchmark** 论文。
> 系统论文的正确评价是"能不能用、在多广的范围内可用、失败模式是什么"，
> 而不是"分数比对手高多少"。论文目前用一个 LLM 评委的标量分数作为主指标，
> 把系统论文写成了刷榜论文。这不是缺陷，但是一个**定位选择**，
> 会决定审稿人用哪套标准衡量它。CRUCIBLE 报为 `minor` + 提示，
> 让作者自觉选择，而不是替他们决定。
