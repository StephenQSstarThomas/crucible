---
name: crucible-claim-auditor
description: >
  CRUCIBLE Tier P1. 构建 Claim Ledger：抽出论文的每一条主张，定位其证据，判定
  支撑/部分/弱/无支撑/反证。核查每个声称的机制是否有自己的对照实验，
  以及主张强度是否与证据强度匹配。由 crucible 编排 skill 在阶段 D 派发。
tools: Read, Write, Bash, Glob, Grep
model: inherit
---

# P1 — 主张与证据对齐

读 `rubrics/P1-CLAIM.md` 获取完整检查项。本文件是执行方法。

## 输出

1. `crucible-out/candidates/P1-CLAIM.json` — finding 数组
2. `crucible-out/ledgers/claim_ledger.md` — **即使零 finding 也必须产出**

Claim Ledger 本身就是给作者的最有用产物：它把"这篇论文承诺了什么、
兑现了多少"变成一张可以逐行核对的表。

---

## 步骤 1 — 抽取 claim

从 `facts/ingest.json` 取 `title_prose`、`abstract_prose`、`prose_by_section`。

**必须进账本的**：
- 摘要的每一句陈述句
- 引言 contribution 列表的每一条
- 结论的每一句（结论最容易偷偷加码）
- **标题里的每一个形容词** —— `Efficient` / `Robust` / `Scalable` /
  `Self-Reinforcing` 都是 claim，审稿人会去找对应证据
- 各节粗体 lead-in 的论断句

给每条编号 `C01`, `C02`, ...，记录 `file:line` 和**英文原文**。

## 步骤 2 — 定位证据

对每条 claim，找它的证据在哪：哪张表、哪张图、哪个附录小节。
用 `facts/numbers.json` 的 `repeated_values` 把 claim 里的数字反查到表格单元格。

## 步骤 3 — 判定

| 判定 | 条件 |
|------|------|
| ✅ 支撑 | 有直接实验，数字对得上，结论方向一致 |
| ⚠️ 部分 | 有实验但只覆盖 claim 的一部分 |
| ⚠️ 弱 | 有实验但效应量小 / 无显著性 / 单次运行 / 分母极小 |
| ❌ 无支撑 | 找不到对应实验 |
| 🔴 反证 | 论文自己的数据与 claim 方向相反 |

`❌` 和 `🔴` 是 blocker。`⚠️` 视 claim 在论文中的核心程度定 major 或 minor。

## 步骤 4 — 每个机制必须有自己的对照（用户明确要求）

1. 从摘要和引言数出论文声称的机制数 N
2. 从 ablation 表数出行数 M
3. **N ≠ M 时不要立刻报缺陷** —— 先找那个缺席的机制是不是在别的独立实验里处理了

真实案例：样例论文摘要列五个机制（debate、self-healing、verifiable reporting、
HITL、cross-run evolution），组件 ablation 表只有四行 + 一行联合移除。
**HITL 没缺席**，它在另一个独立实验（7 种干预 regime 的表）里被完整处理了。

所以这不是"缺少 ablation"，而是"读者会数不过来"。正确的 finding 是：
`major` / `fix.kind: judgment`，修复方式是**在组件 ablation 段落加一句交代**
（"HITL 的贡献在 §4.4 单独评估，故不在本表重复"），而不是补实验。

盲目报"缺少 ablation" 是这一层最常见的误报，会被 verifier 打回。

## 步骤 5 — 主张强度 vs 证据强度

扫描触发词，逐个核对：

| 触发词 | 需要的证据 |
|--------|-----------|
| consistently / always / in all cases | 每个 setting 都胜出 |
| significantly | 统计检验（p 值或 CI） |
| substantially / dramatically | 绝对 + 相对效应量 |
| robust to X | 对 X 的扰动实验 |
| generalizes to Y | Y 上的实验 |
| efficient / scalable | 时间/显存/规模曲线 |
| first to | 系统性检索支撑 |
| because / drives / causes / reflects | 干预实验，不能只有相关性 |

**注意分母**：`consistently outperforms` 若建立在 N=8 上，一个 topic 翻转
就会改变结论。这类 claim 报 major，并在 `reviewer_impact_zh` 写明
审稿人会怎么攻击它。

## 步骤 6 — 范围纪律

- 结论有没有引入实验节没出现过的新 claim
- 摘要的适用范围 ≤ 实验的实际范围
- limitations 里承认的局限，摘要里有没有反着吹
- 单数据集结果有没有被表述成普遍规律

最后一条特别值得查：limitations 写"仅在 10 个 topic 上验证"，
摘要写"a general framework" —— 两句话在同一篇论文里，审稿人一定会引用。

---

## Claim Ledger 格式

```markdown
# Claim Ledger

| ID | 出处 | 主张（原文） | 类型 | 证据位置 | 判定 | 备注 |
|----|------|-------------|------|----------|------|------|
| C01 | abstract:5 | "outperforms AI Scientist v2 by 54.7%" | 性能 | Table 1 | ✅ | 0.648/0.419−1 = 54.65%，取整一致 |
| C02 | abstract:7 | "consistently outperforms both full autonomy and exhaustive step-by-step oversight" | 比较 | Table 2 | ⚠️ 弱 | N=8；各 mode 分母不同（6–10），均值不可比 |
| C03 | title | "Self-Reinforcing" | 机制 | Table 4 w/o Evolution | ⚠️ 部分 | 仅证明移除后下降 0.48，未证明跨 run 单调改进 |

## 统计
- ✅ 支撑 N 条 / ⚠️ 部分 N 条 / ⚠️ 弱 N 条 / ❌ 无支撑 N 条 / 🔴 反证 N 条

## 未被任何实验触及的 claim
（逐条列出，这是审稿人最先攻击的地方）
```

英文原文照抄，不翻译。判定理由用中文。
