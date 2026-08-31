# Desk / immediate-risk card — arXiv:2608.28244

**用途**：arXiv preprint；未指定 venue，因此本卡不判断页数、匿名或 checklist。

## 当前风险

- **Blocker：0** — 稿件可 clean compile，PDF、交叉引用和 bibliography 完整。
- **复现入口 major：1** — `v1.0.1` clone command 当前失败；release identity 在论文、Git、package 与 Zenodo 之间不一致。
- **核心方法 major：3** — 已知 scorer correction 未重算；43/47 是 conditional rate；47 units 只覆盖四个底层 workflow family。
- **Novelty major（PLAUSIBLE）：1** — 与 HEPTAPOD 等最近邻系统的差异未结构化验证。

## 截稿前最低动作

1. 修 release tag/version。
2. 用 scorer v1.2.1 重算并更新全稿数字。
3. 增加 availability 三联指标与 per-family table。
4. 增加 closest-work capability matrix。

若前两项未完成，软件复现与核心 headline 都存在可被审稿人直接验证的问题。
