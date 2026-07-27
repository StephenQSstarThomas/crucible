# Claim Ledger — AutoResearchClaw

论文：`: Self-Reinforcing Autonomous Research with Human-AI Collaboration`（main.tex:76--79）
账本口径：摘要每一句陈述句、引言 contribution 列表每一条、结论每一句、标题每一个形容词、
各节粗体 lead-in 的论断句，全部入账。英文原文照抄，判定理由用中文。

判定五档：✅ 支撑 / ⚠️ 部分 / ⚠️ 弱 / ❌ 无支撑 / 🔴 反证。

---

## A. 标题（main.tex:78）

| ID | 出处 | 主张（原文） | 类型 | 证据位置 | 判定 | 备注 |
|----|------|-------------|------|----------|------|------|
| C01 | title | "Self-Reinforcing" | 机制/形容词 | Table 4 `w/o Evolution` 行 | ⚠️ 部分 | 只证明移除 lesson store 后 quality −0.48、completion −1；未展示随 run 数递增的轨迹。附录 §Design-Space 说 `T_{1/2}=30` "gave the best quality trajectory" 但没有印出任何 trajectory。→ P1-CLAIM-007 |
| C02 | title | "Autonomous Research" | 定位 | Table 1 Full-Auto 行 / Table 2 Full-Auto 行 | ⚠️ 部分 | 全自动模式确实能跑（0.596；end-to-end 8/10 valid），但论文的最优结果与摘要头号数字都来自带干预的 CoPilot。→ P1-CLAIM-011 |
| C03 | title | "with Human-AI Collaboration" | 构念 | Table 2（7 regimes） | ❌ 无支撑 | 实际操作化是 "scripted interventions rather than live human participants"（appendix.tex:764），无真人、无 IRB。测的是"干预调度"，说的是"人机协作"。→ P1-CLAIM-003 |

## B. 摘要（main.tex:143--151）

| ID | 出处 | 主张（原文） | 类型 | 证据位置 | 判定 | 备注 |
|----|------|-------------|------|----------|------|------|
| C04 | abstract:144 | "Automating scientific discovery requires more than generating papers from ideas." | 立场 | — | n/a | 动机句，不需证据 |
| C05 | abstract:145 | "Real research is iterative: hypotheses are challenged from multiple perspectives, experiments fail and inform the next attempt, and lessons accumulate across cycles." | 立场 | — | n/a | 动机句 |
| C06 | abstract:146 | "Existing autonomous research systems often model this process as a linear pipeline: they rely on single-agent reasoning, stop when execution fails, and do not carry experience across runs." | 相关工作 | Table 5 特性表 | ⚠️ 部分 | 由手工特性表断言，未给打勾判据；论文自己也未测量 baseline 的跨 run 行为 |
| C07a | abstract:147 | "structured multi-agent debate for hypothesis generation and result analysis" | 机制 | Table 4 `w/o Debate` | ✅ 支撑 | quality 5.62→4.25（−1.37, p=0.003），方向一致，效应量最大 |
| C07b | abstract:147 | "a self-healing executor with a Pivot/Refine decision loop that transforms failures into information" | 机制 | Table 4 `w/o Self-Healing` | ⚠️ 部分 | completion 10/10→6/10 强支撑"防止终止"；但 Pivot 与 Refine 两个分支从未被分别测量（触发次数、比例、各自收益均未报告），"transforms failures into information" 无直接证据 |
| C07c | abstract:147 | "verifiable result reporting that prevents fabricated numbers and hallucinated citations" | 机制 | Table 4 `w/o Verification` + Fabrication 列 | 前半 ✅ / 后半 ❌ | fabricated numbers：移除后 accept 3/10→5/10 且 5 篇里 3 篇含无记录数值 ✅。hallucinated citations：全文零测量，无 w/o Citation-Verification 行。→ P1-CLAIM-008 |
| C07d | abstract:147 | "human-in-the-loop collaboration with seven intervention modes spanning full autonomy to step-by-step oversight" | 机制 | Table 2 + 附录 Table 8 | ⚠️ 部分 | 七个模式确实各有实验（这一点比其它机制做得更细）；但构念是脚本注入，见 C03 |
| C07e | abstract:147 | "cross-run evolution that converts past mistakes into future safeguards" | 机制 | Table 4 `w/o Evolution` | ⚠️ 弱 | −0.48 quality / −1 completion，n=10、best-of-3、无 p 值、无 CI；"converts past mistakes into future safeguards" 的过程本身未被观测 |
| C08 | abstract:148 | "On ARC-Bench, a 25-topic experiment-stage benchmark, AutoResearchClaw outperforms AI Scientist v2 by 54.7%." | 性能 | Table 1 | ✅ 算术 / ⚠️ 范围 | 0.648/0.419−1 = 54.65% → 54.7% 取整一致 ✅；但 0.648 是 CoPilot（含人类干预）行，未加限定；同自主度对比为 42.2%。另：§4.1 定义的 ARC-Bench 是 25 ML + 20 科学 = 45 topic，摘要只说 25。→ P1-CLAIM-011 |
| C09 | abstract:149 | "precise, targeted collaboration at high-leverage decision points consistently outperforms both full autonomy and exhaustive step-by-step oversight" | 比较 | Table 2 | ⚠️ 弱 | N=8（CoPilot 有效 run 数）；七个 mode 的 Valid 分母为 6--10 且互不相同，均值取自不同 topic 子集，不可比；单次运行；无逐 topic 表。→ P1-CLAIM-005 |
| C10 | abstract:150 | "We position AutoResearchClaw as a research amplifier that augments rather than replaces human scientific judgment." | 定位 | — | n/a | 立场声明，不作证据要求 |

## C. 引言 contribution 列表与机制段（intro.tex）

| ID | 出处 | 主张（原文） | 类型 | 证据位置 | 判定 | 备注 |
|----|------|-------------|------|----------|------|------|
| C11 | intro:28 | "with a confidence-driven SmartPause mechanism that routes decisions to the researcher only when system uncertainty is high" | 机制 | — | ❌ 无支撑 | 全文零测量：无触发次数、无阈值曲线、无 w/ vs w/o 对照；且它只在 CoPilot 生效，破坏 Pre/Post 分解。→ P1-CLAIM-010 |
| C12 | intro:30 | "These mechanisms interact: past lessons inform debate, debate improves experiment choices, self-healing keeps the pipeline moving, and verification ensures outputs are grounded in actual results." | 交互 | Table 4 联合移除行 | ⚠️ 部分 | 只测了 debate×self-healing 一对；lessons→debate、debate→experiment choices 两条链路无对照 |
| C13 | intro:32 | "our main contribution is AutoResearchClaw, an open-source multi-agent system ..." | 贡献 | main.tex:154 GitHub 链接 | ✅ 支撑 | 有仓库链接 |
| C14 | intro:33 | "We introduce ARC-Bench, a 25-topic benchmark focused on the experiment stage, evaluated with a rubric-assisted LLM judge." | 贡献 | 附录 Table 9（T01--T25）+ 附录 rubric box | ✅ 支撑 | 25 个 topic 全部列出且 ID 无缺漏。注：§4.1 称其为 ML01--ML25，附录称 T01--T25，命名不一致；20 个科学任务（P/B/S）无任何 topic 清单 |
| C15 | intro:34 | "On this benchmark, AutoResearchClaw outperforms AI Scientist v2 by 54.7%." | 性能 | Table 1 | ✅ 算术 / ⚠️ 范围 | 同 C08 |
| C16 | intro:35 | "targeted human input at high-leverage decision points consistently outperforms both full autonomy and dense step-by-step oversight" | 比较 | Table 2 | ⚠️ 弱 | 同 C09 |
| C17 | intro:36 | "Further analysis shows that the modular design of AutoResearchClaw can connect to domain-specific scientific experiments, including high-energy theory." | 泛化 | Table 3 | ⚠️ 部分 | HEP 是三列中最低分（0.489）且在 Overall 里只占 1 个 run；HEP agent 架构自承 "the ColliderAgent architecture we directly adopt here"；且论文做的是 HEP phenomenology（MadGraph/Delphes）而非 "high-energy theory" |
| C18 | intro:37 | "We discuss safeguards for responsible use, including citation verification, claim grounding, and transparency requirements, in Appendix" | 交叉引用 | 附录 §Ethics | ✅ 支撑 | 附录确有对应段落 |

## D. 相关工作（related_work.tex）

| ID | 出处 | 主张（原文） | 类型 | 证据位置 | 判定 | 备注 |
|----|------|-------------|------|----------|------|------|
| C19 | related:6 | "no prior system combines end-to-end execution with multi-agent debate, self-healing, anti-fabrication verification, and cross-run evolution" | 优先性 | Table 5 | ⚠️ 弱 | 6 个系统的手工表，无检索协议、无 ✓/✗/~ 判据。→ P1-CLAIM-015 |
| C20 | related:16(caption) | "Only AI Scientist v2 and AutoResearchClaw provide end-to-end autonomous execution from idea to paper; Agent Laboratory and ResearchAgent stop short." | 优先性 | Table 5 | ⚠️ 弱 | 同上；且 "ResearchAgent" 一列在正文里没有对应引用（正文写的是 AI-Researcher） |
| C21 | related:12 | "across seven intervention regimes, we find that targeted intervention at high-leverage decision points consistently outperforms both full autonomy and exhaustive step-by-step oversight" | 比较 | Table 2 | ⚠️ 弱 | 同 C09（这是 "consistently" 的第三次出现） |

## E. 方法节（system.tex）的可检验断言

| ID | 出处 | 主张（原文） | 类型 | 证据位置 | 判定 | 备注 |
|----|------|-------------|------|----------|------|------|
| C22 | system:69 | "By making failure recoverable, AutoResearchClaw can pursue higher-risk hypotheses that would be abandoned under a brittle execution model." | 机制 | — | ❌ 无支撑 | 从未测量"假设风险度"，也没有 w/ vs w/o self-healing 的假设分布对比 |
| C23 | system:84 | "Claims in strict sections (Abstract, Results, Experiments) that cannot be matched to a registry entry trigger document rejection." | 机制 | Table 4 Fabrication 列 | ⚠️ 部分 | 只有"开/关 verification 时是否出现捏造值"的二元结论，没有 rejection 触发率、误报率（论文自称做了 per-condition scoping "to prevent cross-condition false positives"，但假阳率未报） |
| C24 | system:91 | "References classified as Hallucinated are removed before any draft is finalized." | 机制 | — | ❌ 无支撑 | 见 C07c；附录 §Writing-Quality Audit 反而报告本系统输出中仍有 "Bracket-style pseudo-citations (2/20)" |
| C25 | system:98 | "Full automation reduces output quality at critical junctures where domain judgment matters." | 前提 | Table 2 Full-Auto 行 | ✅ 支撑 | Full-Auto 的 4.03/25% 是七个 mode 里最低，方向一致 |
| C26 | system:115 | "The threshold adapts based on historical approval patterns" | 机制 | — | ❌ 无支撑 | SmartPause 自适应从未被观测。→ P1-CLAIM-010 |
| C27 | system:134 | "This design means that recent failures strongly constrain subsequent runs, while lessons from completed, successful lines of work gradually fade from prominence." | 机制 | 附录 §Design-Space（定性） | ⚠️ 弱 | 只有半定量描述（"influence 3--5 subsequent runs"），无数据 |

## F. 实验节粗体 lead-in 与关键论断（experiment.tex）

| ID | 出处 | 主张（原文） | 类型 | 证据位置 | 判定 | 备注 |
|----|------|-------------|------|----------|------|------|
| C28 | exp:17 | "All frameworks use the same LLM backbone (GPT-5.3-codex) and the same sandboxed execution environment ... This controlled setup isolates the contribution of system design from backbone capability." | 公平性 | §4.3 exp:86 | 🔴 反证 | 同一篇论文写 "Each specialized agent runs inside a Claude Code subprocess with the requisite packages pre-installed"。→ P1-CLAIM-004 |
| C29 | exp:67 | "AutoResearchClaw outperforms all baselines across all dimensions." | 比较 | Table 1 | ⚠️ 部分 | CoPilot 行四维全胜 ✅；Full-Auto 行 Code Dev 0.938 < AIDE-ML 0.958。→ P1-CLAIM-016 |
| C30 | exp:67 | "Even in Full-Auto mode without human intervention, AutoResearchClaw (0.596) substantially exceeds both baselines, indicating that the gains are primarily driven by system design rather than human input." | 归因 | Table 1 | ✅ 方向 / ⚠️ 弱 | 归因成立：人类干预只占对 AISv2 总差距的 22.7%（0.052/0.229）✅。但 "substantially" 对应的效应量 0.596−0.511 = 0.085，无方差、无 CI、单次运行 |
| C31 | exp:69 | "The largest advantage is on Result Analysis." + "a 100.4% relative improvement" | 性能 | Table 1 | ✅ 支撑 | 0.523/0.261−1 = 100.38% → 100.4% ✅；RA 也确为四维中相对差距最大者 |
| C32 | exp:69 | "The advantage directly reflects multi-agent debate at the result analysis stage and the verified result registry" | 因果 | Table 4 | ⚠️ 部分 | 有 debate / verification 的移除对照 ✅，所以不是纯相关性措辞；但 ablation 跑在另一套设置（10 topic、end-to-end quality 1--10、best-of-3），并没有在 RA 这个指标上做开/关对照 |
| C33 | exp:71 | "Code Development is competitive; execution separates the systems." | 比较 | Table 1 | ✅ 支撑 | CD 四个系统 0.712--0.968，CE 0.415--0.578，描述与表一致 |
| C34 | exp:71 | "AIDE-ML's execution success rate (0.415) ... self-healing executor raises execution success to 0.562 / 0.578" | 指标身份 | Table 1 + 附录 rubric | ⚠️ 部分 | CE 是加权 rubric 分（含 multi-seed dispersion leaf），不是执行成功率。→ P1-CLAIM-017 |
| C35 | exp:73 | "This pattern confirms that self-healing is most valuable on topics where the first implementation attempt is unlikely to succeed." | 因果 | 无表 | ⚠️ 弱 | 跨系统失败计数（2 vs 6）不能 confirm 单一组件；两个计数无逐 topic 表可核。→ P1-CLAIM-019 |
| C36 | exp:87 | "This design is what enables AutoResearchClaw to reproduce experiments across heterogeneous scientific fields without per-domain engineering effort." | 因果 | §4.3 exp:85 | 🔴 反证 | 前两句刚列出三套手工领域技能包 + 领域 rubric 重写。→ P1-CLAIM-013 |
| C37 | exp:120 | "Sandboxed domain agents are necessary for cross-domain coverage." | 因果 | Table 3 | ⚠️ 弱 | 无"关掉领域 agent"的对照；baseline 的 0 分主要由环境预装差异造成。→ P1-CLAIM-004 |
| C38 | exp:123 | "AutoResearchClaw correctly reproduces the predicted shape and numerical cross-section values" | 性能 | — | ❌ 无支撑 | 没有任何图或数字展示这次复现；HEP 列只有一个聚合分 0.489 |
| C39 | exp:113 | Table 3 Overall = 0.867 / 0.090 / 0.084 | 性能 | Table 3 caption | 🔴 反证 | 按 caption 的 20 任务 run-weighted 口径应为 0.698；反解出实际分母是 10 个 run，HEP 只占 1。→ P1-CLAIM-002 |
| C40 | exp:124 | "both baselines score zero on physics and biology because their sandboxes do not include the required scientific software; AutoResearchClaw's domain-skill installation step closes this gap" | 因果 | Table 3 | ⚠️ 弱 | 因果方向可能成立，但没有"给 baseline 同样镜像"的对照 |
| C41 | exp:133 | "More intervention does not monotonically improve quality." | 趋势 | Table 2 | ✅ 支撑 | Thorough（8 次干预，4.86）低于 Gate-Only（3 次，5.03），非单调成立 |
| C42 | exp:133 | "CoPilot ... with 19 targeted interventions. Step-by-Step requires 29 interventions" | 数值 | Table 2 Interventions 列 | 🔴 反证 | 表里是 6 和 23；19/29 在全文任何表中都不存在。→ P1-CLAIM-001 |
| C43 | exp:133 | "On matched topics, CoPilot beats Full-Auto by +3.21 and beats Step-by-Step by +2.16." | 数值 | — | ❌ 无支撑 | 无 matched-topic 表；表内差值为 3.24 与 2.08，与之不符 |
| C44 | exp:136 | "Pre-Experiment and Post-Experiment HITL address different failure modes." + "CoPilot is best because it spans both halves" | 分解 | Table 2 + 附录 Table 8 | ⚠️ 部分 | CoPilot = {5,8,9,14,17,20} **+ smart pauses** ≠ Pre ∪ Post，分解不干净。→ P1-CLAIM-010 |
| C45 | exp:136 | "Post-Experiment produces some of the strongest individual papers but is valid on only 6/10 topics" | 定性 | Table 2（仅均值） | ❌ 无支撑 | "strongest individual papers" 需要逐 topic 分数，论文没印 |
| C46 | exp:138 | "Gate-Only provides a cost-effective middle ground." + "raises accept rate from 25% to 50% and is the only mode achieving 10/10 validity" | 比较 | Table 2 | ⚠️ 部分 | 25%→50% 与 10/10 都对；但 Table 2 里 Step-by-Step 同为 10/10，"the only mode achieving 10/10 validity" 与表不符。→ P1-CLAIM-020 |
| C47 | exp:145 | "To isolate the contribution of each mechanism ... Each row removes one mechanism and keeps the others intact." | 覆盖度 | Table 4 | ⚠️ 部分 | 五机制只有四行；HITL 在 §4.4 单独评估但正文未交代。→ P1-CLAIM-009 |
| C48 | exp:148 | "Autonomous research agents are stochastic and path-dependent ... We therefore adopt a best-of-N protocol" | 方法说明 | Table 4 caption | ✅ 已交代 | 这一段正确解释了 Table 4 Full 行（5.62 / 3-of-10）与 Table 2 Full-Auto 行（4.03 / 25%）为何不同，位置也正确（紧邻 Table 4）。**不报 finding。** 但同一论证削弱了 Table 1/2 的单次运行口径 → P1-CLAIM-012 |
| C49 | exp:169 | "Each mechanism addresses a distinct failure mode, even under a favorable rerun budget." | 机制 | Table 4 | ⚠️ 部分 | 四行方向都对；但只有 debate 一行有 p 值，其余三行无显著性检验 |
| C50 | exp:170 | "Multi-agent debate is the largest quality contributor (−1.37, p=0.003)" | 效应量 | Table 4 | ✅ 支撑 | 5.62−4.25 = 1.37 ✅，且确为四行中最大 quality 降幅。检验方法未指明（全文唯一 p 值） |
| C51 | exp:170 | "Cross-run evolution provides a moderate reliability gain (−0.48 quality, −1 completion)" | 效应量 | Table 4 | ⚠️ 弱 | 5.62−5.14 = 0.48 ✅、10−9 = 1 ✅；但 n=10、无检验、1 个 topic 的完成差在二项意义上几乎无信息 |
| C52 | exp:172 | "Verification is the integrity backstop." + "3 of those 5 papers contain values absent from any measurement record" | 机制 | Table 4 Fabrication 列 | ✅ 支撑 | accept 3/10→5/10 与 ‡ 标注一致，方向与解释自洽 |
| C53 | exp:175 | "The mechanisms interact super-additively." | 交互 | Table 4 | 🔴 反证（quality）/ ✅（completion） | quality 可加预测 3.46 vs 实测 3.47；completion 可加预测 6/10 vs 实测 4/10。论文把 quality 3.47 列为超可加证据。→ P1-CLAIM-006 |
| C54 | exp:192--194 | "The T10 case shows why execution success alone is not enough." 等三条观察 | 案例 | 附录 Table 10 | ✅ 支撑 | 单案例定性结论，措辞与证据强度匹配（未从单案例推普遍规律） |
| C55 | exp:15 | "Two independent agent reviewers run the strict judge in parallel ... Details and inter-rater agreement are in Appendix" | 测量效度 | 附录 §Strict Judge | ⚠️ 弱 | 附录只给 "Mean per-leaf |Δ| < 0.10 across the audited subset"，无 κ/ICC、无子集规模、人类专家覆盖率未给 |

## G. 结论（conclusion.tex:6，逐句）

| ID | 出处 | 主张（原文） | 类型 | 证据位置 | 判定 | 备注 |
|----|------|-------------|------|----------|------|------|
| C56 | concl:6 | "unifies structured debate, self-healing execution, verifiable result reporting, cross-run evolution, and human-in-the-loop collaboration in a single self-reinforcing system" | 总结 | Table 4 + Table 2 | ⚠️ 部分 | "self-reinforcing" 见 C01 |
| C57 | concl:6 | "outperforms AI Scientist v2 by 54.7%, with the largest gains on result analysis where multi-agent debate and verified reporting produce hypothesis-aligned, grounded conclusions" | 性能+因果 | Table 1 + Table 4 | ✅ 算术 / ⚠️ 归因 | 见 C08、C32 |
| C58 | concl:6 | "consistently outperforms both full autonomy (25%) and exhaustive step-by-step oversight (50%), establishing that precise human-AI collaboration is a more effective paradigm than either extreme" | 比较 | Table 2 | ⚠️ 弱 | "consistently" 第四次出现 + "establishing" 升格；且构念为脚本干预。→ P1-CLAIM-005 / 003 |
| C59 | concl:6 | "Component ablation confirms that the mechanisms are complementary: debate drives quality, self-healing drives completion, verification enforces integrity, and their combined removal is super-additive." | 交互 | Table 4 | 前三项 ✅ / 末项 🔴 | 前三个归因方向与表一致；"combined removal is super-additive" 在 quality 上被反证。→ P1-CLAIM-006 |
| C60 | concl:6 | "a research amplifier that accelerates scientific exploration while keeping verifiability at the center" | 效率 | — | ❌ 无支撑 | 全文无任何时间/成本/人力对比曲线；唯一成本数字是附录伦理段的 "$3--15 in LLM usage"，且无人类基线。"accelerates" 属于 L3.6 触发词但无成本或规模证据 |

---

## 统计

- ✅ 支撑：**13** 条（C07a, C13, C14, C18, C25, C29-CoPilot 行, C30 方向, C31, C33, C41, C48, C50, C52, C54 —— 其中 C29/C30/C57 为部分计入）
- ⚠️ 部分：**19** 条
- ⚠️ 弱：**11** 条
- ❌ 无支撑：**9** 条（C03, C11, C22, C24, C26, C38, C43, C45, C60）
- 🔴 反证：**5** 条（C28, C36, C39, C42, C53 —— C53 仅 quality 维度反证）

（部分条目跨两档，按主判定计数；总条目 60 条。）

## 未被任何实验触及的 claim（审稿人最先攻击的地方）

1. **C03 "Human-AI Collaboration"（标题级）** —— 零真人参与，全部是作者事先写好的脚本注入；
   唯一披露在 appendix.tex:764 的最后一句。且 CoPilot 的注入文本点名了 Full-Auto 在同一
   topic 上的具体失败（附录 Table 10），存在 oracle 泄漏。
2. **C11 / C26 SmartPause** —— 引言与 §3.4 各占一段，实验部分一个数都没有；
   它还只在 CoPilot 生效，直接破坏 §4.4 的 Pre/Post 分解论证。
3. **C24 hallucinated citations** —— 四层引用验证管线写了整段、Table 5 把它列为独家能力，
   但没有任何 hallucination 率、层级命中率或开/关对照。附录审计里的
   "Bracket-style pseudo-citations (2/20)" 反而是负面证据。
4. **C22 "can pursue higher-risk hypotheses"** —— 假设风险度从未被定义或测量。
5. **C38 "correctly reproduces the predicted shape and numerical cross-section values"** ——
   没有图、没有数字、没有与参考值的比对，只有一个 0.489 的聚合分。
6. **C43 "+3.21 / +2.16 on matched topics"** —— 没有 matched-topic 表；
   表内可算出的差值是 3.24 与 2.08。
7. **C45 "some of the strongest individual papers"** —— 逐 topic 分数全文未印。
8. **C60 "accelerates scientific exploration"** —— 无任何时间/成本/人力对比。
9. **跨 run 学习曲线（C01/C07e/C27）** —— "Self-Reinforcing" 是标题词，
   但论文没有任何 run-index vs 表现的图表。

## 需要注意的"看起来像缺陷但其实已被交代"（不报 finding）

- **Table 4 的 Full 行（5.62 / 3-of-10）与 Table 2 的 Full-Auto 行（4.03 / 25%）数值不同** ——
  §4.5 的 "Best-of-N protocol" 段落已解释（Table 4 用 best-of-3，Table 2 为单次运行），
  解释存在且位置正确（紧邻该表）。判定 ✅ 已交代。
- **Table 4 里 `w/o Verification` 的 accept（5/10）高于完整系统（3/10）** ——
  已用 ‡ 脚注 "Score inflated by removing the verification gate" 与正文
  "3 of those 5 papers contain values absent from any measurement record" 解释清楚。
  判定 ✅ 已交代。
- **五个机制 vs 四行 ablation** —— HITL 并非缺席，它在 §4.4 用 7 个 regime 单独评估，
  覆盖度甚至高于其它机制。因此**不是"缺少 ablation"**，而是缺一句交叉引用；
  对应 P1-CLAIM-009，`fix.kind: judgment`，不需要补实验。
