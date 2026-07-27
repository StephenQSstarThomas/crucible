# P1-CLAIM — 主张与证据对齐

**判据**：论文说的每一句话，有没有对应的实验撑着。

这是用户问题里的核心一条：
> "claim是否达成，做得实验是否全面严谨，对于每一个claim实现的对比试验等有无落实"

**默认 severity**：无证据支撑的核心 claim = `blocker`；夸大 = `major`；范围溢出 = `major`。

**采集器**：`bin/numbers.py` + `agent-read`（claim 抽取无法脚本化）

---

## 核心产物：Claim Ledger（主张账本）

CRUCIBLE 为每篇论文构建一张表。**这张表本身就是给作者的最有用产出**，
即使一条 finding 都没有。

| claim_id | 出处 | 主张原文 | 类型 | 证据位置 | 判定 |
|----------|------|----------|------|----------|------|
| C01 | abstract:5 | "outperforms AI Scientist v2 by 54.7%" | 性能 | Table 1 | ✅ 支撑 |
| C02 | abstract:7 | "targeted collaboration ... consistently outperforms both" | 比较 | Table 2 | ⚠️ 部分 |
| C03 | intro:12 | "cross-run evolution converts past mistakes into future safeguards" | 机制 | Table 4 w/o Evolution | ⚠️ 弱 |
| C04 | intro:15 | "prevents fabricated numbers and hallucinated citations" | 机制 | Table 4 w/o Verification | ✅ 支撑 |

判定五档：

- **✅ 支撑** — 有直接实验，数字对得上，结论方向一致
- **⚠️ 部分** — 有实验但只覆盖 claim 的一部分（如 claim 说 "consistently"，实验只在 1 个数据集上）
- **⚠️ 弱** — 有实验但效应量小 / 无显著性 / 单次运行
- **❌ 无支撑** — 找不到对应实验
- **🔴 反证** — 论文自己的数据与 claim 方向相反

---

## L1. Claim 抽取的完备性

| ID | 检查项 |
|----|--------|
| L1.1 | 摘要中的每一句陈述句都进账本 |
| L1.2 | 引言 contribution 列表的每一条都进账本 |
| L1.3 | 结论中的每一句都进账本（结论最容易偷偷加码） |
| L1.4 | 标题中的每一个形容词都进账本（"Efficient"、"Robust"、"Scalable" 都是 claim） |
| L1.5 | 每个 section 的粗体 lead-in 论断都进账本 |

> L1.4 不是吹毛求疵。标题里写 `Efficient`，审稿人就会找运行时间/显存的对比表；
> 找不到就是一条 weakness。形容词是最廉价的 claim，也是最常被漏掉证据的。

## L2. 每个机制必须有自己的对照 ← 用户明确要求的一条

论文若声称由 N 个机制构成，且声称每个机制都有贡献，则**必须有 N 行 ablation**，
每行只移除一个机制。

| ID | 检查项 | severity |
|----|--------|----------|
| L2.1 | 摘要/引言列出的每个机制，在 ablation 表中有对应行 | blocker |
| L2.2 | ablation 表中每一行只改变一个变量 | major |
| L2.3 | 声称"机制间有交互/超可加"时，有联合移除行 | major |
| L2.4 | ablation 与主实验用同一套 topic/数据/预算 | blocker |
| L2.5 | ablation 的 baseline 行（完整系统）数值与主表一致 | blocker |
| L2.6 | 每个机制的贡献有效应量，不只有方向 | major |

> **L2.1 在样例论文上的判定**：摘要列出五个机制——debate、self-healing executor、
> verifiable result reporting、human-in-the-loop、cross-run evolution。
> 组件 ablation 表（Table 4）有 debate / self-healing / evolution / verification
> 四行 + 一行联合移除。**HITL 没有出现在组件 ablation 中**——它被放在
> 另一个独立实验（Table 2，7 种干预 regime）里处理了。
>
> 这不是缺陷，但**必须在正文里说清楚**，否则审稿人会数：五个机制、四行 ablation，
> 少一个。CRUCIBLE 报为 `major`，修复方式是加一句交代，而非补实验。
> 这正是"看起来像缺陷但其实是表述问题"的典型，也是为什么 P1 的 finding
> 必须经 verifier 对抗验证——盲目报"缺少 ablation"会是误报。
>
> **L2.5 在样例论文上的判定**：Table 4 的 `Full AutoResearchClaw` 行是
> Quality 5.62 / Accept 3/10，而 Table 2 的 Full-Auto 行是 4.03 / 25%（2/8）。
> 两者数字不同。论文在 §4.5 的 "Best-of-N protocol" 段落里解释了原因
> （Table 4 用 best-of-3，Table 2 是单次运行）。**解释存在且位置正确** → 判定为
> ✅ 已交代，不报 finding。CRUCIBLE 必须能区分"矛盾"与"已被解释的差异"，
> 否则会把认真的作者淹没在误报里。

## L3. Claim 强度与证据强度匹配

| ID | 检查项 | 触发词 |
|----|--------|--------|
| L3.1 | "consistently" / "always" / "in all cases" 有全覆盖证据 | 需每个 setting 都胜出 |
| L3.2 | "significantly" 有统计检验 | 需 p 值或置信区间 |
| L3.3 | "substantially" / "dramatically" 有效应量 | 需绝对+相对幅度 |
| L3.4 | "robust to X" 有对 X 的扰动实验 | 需变化 X 的对照 |
| L3.5 | "generalizes to Y" 有 Y 上的实验 | 需跨域/跨数据集 |
| L3.6 | "efficient" / "scalable" 有成本或规模曲线 | 需时间/显存/参数量 |
| L3.7 | "first to ..." 有 related work 支撑 | 需明确说明前作为何不算 |
| L3.8 | 因果性表述有干预实验，而非仅相关 | "because"、"drives"、"causes" |

> L3.8 高频命中：`"The advantage directly reflects multi-agent debate at the result
> analysis stage and the verified result registry"` —— 这是一个**因果**断言。
> 支撑它需要的是 ablation（有/无 debate 的对比），而该句所在段落引用的是主结果表。
> ablation 确实存在于 Table 4，所以这条是 ✅；但若 ablation 不存在，
> 这就是典型的"用相关性措辞冒充因果结论"。

## L3b. 构念效度：测的东西是不是说的东西

**这是 P1 层最容易整层漏掉的一类缺陷，来自真实评审的验证。**

前面的 L3 检查的是"证据够不够强"。L3b 检查的是一个更根本的问题：
**这个实验测量的对象，和 claim 里说的那个概念，是同一个东西吗？**

证据可以完全充分、统计可以完全干净、数字可以完全真实，而 claim 依然不成立——
因为实验测的根本不是它声称的那个构念。

| ID | 检查项 | severity |
|----|--------|----------|
| L3b.1 | claim 中的每个抽象名词，在实验中有明确的操作化定义 | major |
| L3b.2 | 该操作化与该名词的**通常理解**一致 | blocker |
| L3b.3 | 用代理指标时，代理与目标的关系有论证或引用 | major |
| L3b.4 | 用模拟/脚本替代真实对象时，替代的有效性有讨论 | blocker |
| L3b.5 | 结论的措辞回到构念层面时，范围没有被悄悄放大 | blocker |

**真实案例（三位审稿人中的两位独立提出）**：

论文的核心 claim 之一是 *human-AI collaboration*：
> targeted collaboration at high-leverage decision points consistently
> outperforms both full autonomy and exhaustive step-by-step oversight

实验做的是：七种干预 regime，每种在预定阶段注入**预先写好的脚本化专家 payload**。

审稿人的判定：
> the HITL study uses **scripted expert interventions rather than live human
> collaborators** ... so the result is better described as an
> **intervention-schedule ablation** than evidence about real human-AI collaboration
>
> This would test whether the gains come from the proposed intervention schedule
> rather than from **high-quality expert content injected at favorable stages**

关键点：**论文如实披露了干预是脚本化的**（附录里写了）。
所以这不是 P0-INTEG 的诚信问题，也不是 L3 的"证据不足"——
证据对于"干预时序消融"这个 claim 是充分的。

问题在于 claim 说的是 *collaboration*（一个关于人与系统互动的构念），
而测的是 *schedule*（一个关于时序的变量）。**两者不是同一个东西。**
而且存在一个未被排除的竞争解释：增益可能来自注入内容的质量，而非注入的位置。

**检查方法**：
1. 从 claim 里挑出抽象名词（collaboration、robustness、reasoning、
   understanding、creativity、autonomy、generalization……）
2. 去实验节找它的操作化：具体测了什么变量
3. 问三个问题：
   - 换一个人来读，会认为这个操作化就是那个名词吗？
   - 有没有一个同样能解释结果的竞争构念？（此例：内容质量 vs 注入位置）
   - 论文有没有做能区分两者的对照？（此例：等 token 量的泛化 feedback、
     随机位置的干预门 —— 都没做）
4. 三问中任意一问失败 → 报 major；claim 直接建立在错配的构念上 → blocker

**修复方向通常不是补实验，而是改措辞。** 把
"human-AI collaboration outperforms full autonomy" 改成
"targeted intervention schedules outperform uniform ones under scripted
expert payloads"，claim 立刻与证据对齐，且不损失任何真实贡献。
审稿人明确建议了这条路：
> A more defensible framing would be that the results **suggest improved
> robustness on ARC-BENCH under the authors' evaluation protocol**, rather
> than establishing broad superiority.

## L4. 范围纪律（Scope discipline）

| ID | 检查项 | severity |
|----|--------|----------|
| L4.1 | 结论没有引入实验节没出现过的新 claim | blocker |
| L4.2 | 摘要的适用范围 ≤ 实验的实际范围 | major |
| L4.3 | 标题承诺的东西论文真的做了 | major |
| L4.4 | 单数据集结果没有被表述成普遍规律 | major |
| L4.5 | limitations 里承认的局限，摘要里没有反着吹 | blocker |
| L4.6 | 定性观察没有被写成定量结论 | major |

> L4.5 是审稿人最反感的模式：limitations 写"仅在 10 个 topic 上验证"，
> 摘要写"a general framework for autonomous research"。两句话都在同一篇论文里。

## L5. 数字—叙述锚定

| ID | 检查项 |
|----|--------|
| L5.1 | 每个正文中出现的数字，能定位到它来自哪张表/图的哪个单元格 |
| L5.2 | 正文对表格的**趋势**描述与表格实际趋势一致 |
| L5.3 | "最优/最高/最低"的表述与表中加粗一致 |
| L5.4 | 正文声称的"提升"方向与指标方向一致（越低越好的指标不要说"更高更好"） |
| L5.5 | 引用的对比对象（"outperforms X by Y%"）中 X 确实在表中 |

> L5.1 是本 tier 最有价值的机械检查。样例论文中
> `"CoPilot achieves ... with 19 targeted interventions"` 与
> `"Step-by-Step requires 29 interventions"` 两个数字**在任何表格里都不存在**
> （表 2 对应单元格是 6 和 23）。这既是 I1.2 的数值矛盾，
> 也是 L5.1 的锚定失败——两个 tier 都会命中，合并为一条 `blocker`。
