# CRUCIBLE 审查报告 — HEPLocalAgent 1.0

## 写作来源判断（非取证结论）

> **档位：AI深度参与**
>
> 当前可得证据更符合“AI深度参与”。这是一项来源风险判断，不是作者身份或诚信的取证结论。

**支持该判断的信号**：

- `direct` — 论文明确声明 ChatGPT 参与了 “manuscript drafting” 和 “figure preparation”（`main.tex:416-425`），已经超过单纯 grammar polishing。
- `supporting` — 软件仓库 `AI_ASSISTED_DEVELOPMENT.md` 另行披露 ChatGPT/Claude 参与实现、软件架构、文档、review 与 code patches，AI 参与贯穿了被论文描述的项目。

**反对信号 / 其他解释**：

- `direct` — 同一声明明确说 scientific objectives、requirements、runs、technical/scientific claims 由作者定义、执行、检查并负责；没有声明全文由模型生成。
- `high-specificity` — TeX 源码没有 assistant 自述、聊天角色、生成指令或 placeholder citation 泄漏。
- `weak` — 全文术语、限制和 headline 数字传播总体一致；但终稿一致性不能区分人工写作与充分人工修订过的 AI 初稿。

**缺失证据**：arXiv source package 不含 manuscript Git history，也没有 drafting prompts、聊天日志、逐稿 diff 或作者写作记录。软件仓库历史不能证明各段论文文字的起源。

**方法限制**：终稿文风不能可靠区分人类写作、AI 改写与人类重写 AI 初稿。本结论主要依赖作者自己的直接 disclosure，因此足以支持 `AI深度参与`，不足以支持 `全AI`；不输出未经校准的百分比。

---

**稿件**：[arXiv:2608.28244](https://arxiv.org/abs/2608.28244)，submitted 2026-08-28

**主文件**：`main.tex`（唯一 `\documentclass`）

**用途**：公开 arXiv preprint；未套用双盲或特定 venue 规则

**源码包 SHA-256**：`dd12fdbf576d8c9a9f7e068e4924ce2243eb761e7186bbbfad53df1527c7aeed`

**审查方式**：TeX source + Tectonic PDF + 全 24 页视觉复核 + 公开 release/Zenodo 核验；未提供原始实验 runs

## 摘要

| Tier | blocker | major | minor | nit | refuted |
|------|--------:|------:|------:|----:|--------:|
| P0-BUILD | 0 | 1 | 0 | 0 | 0 |
| P0-INTEG | 0 | 0 | 0 | 0 | 2 |
| P0-SURF | 0 | 0 | 0 | 1 | 0 |
| P1-CLAIM | 0 | 0 | 1 | 0 | 0 |
| P2-RIGOR | 0 | 3 | 1 | 0 | 0 |
| P3-DEF | 0 | 1 | 0 | 0 | 0 |
| P4-PRES | 0 | 0 | 1 | 1 | 1 |

**一句话结论**：稿件的限制披露、自洽性与最终 PDF 明显高于一般预印本；当前最需要处理的不是语言，而是不可执行的 release version、已知有误却未重算的 scorer、把 43/47 条件正确率与本地系统可用性分开，以及四个底层 workflow family 带来的有效覆盖不足。

## ⚠️ 应该先修（major）

### [P0-BUILD-001] 论文给出的唯一安装 tag 不存在，版本标识四处冲突

**位置**：`main.tex:50-51, 229, 431`；公开代码 commit `feeccfb10...`。

**原文**：

> git clone --branch v1.0.1 https://github.com/AadarshSingh0/HEPLocalAgent.git

**复核**：

```text
git clone --depth 1 --branch v1.0.1 ...
fatal: Remote branch v1.0.1 not found in upstream origin

feeccfb10... -> refs/tags/v0.1.1
pyproject.toml -> version = "0.1.1"
src/hep_agent/__init__.py -> __version__ = "0.1.0"
Zenodo 21934091 -> metadata.version = "v1.0.1"
Zenodo related Git URL -> .../tree/v0.1.1
```

**问题**：软件论文的复制即用入口失效，而且论文、Git、package runtime 与 Zenodo 没有同一个 canonical version。

**建议**（需要作者选择）：

- 若正式 release 应为 `v1.0.1`：在 archived commit 上发布该不可变 tag，并同步 `pyproject.toml` 与 `__version__`。
- 若实际 release 是 `v0.1.1`：全文、title/abstract、clone command 与 Zenodo version 一起改为 `v0.1.1`，同时把 `__version__` 从 `0.1.0` 改为 `0.1.1`。
- CI 增加一个文档安装命令 smoke test，防止论文中的 tag 再次漂移。

### [P2-RIGOR-001] 核心结果仍由已知有误的 v1.2 scorer 产生

**位置**：`appendices/evaluation_protocol.tex:141-158`，`main.tex:437-439`。

**原文**：

> All workflow-construction counts reported in this paper are therefore v1.2 quantities. The companion benchmark paper subsequently corrected two native scorers in v1.2.1...

**问题**：四个 workflow family 中两个受到 scorer correction 影响。论文推测 v1.2.1 会提高 unnormalized counts、缩小 7/47 → 19/47 的 gap，却没有实际重算。透明披露值得肯定，但不能替代可以离线完成的 corrected measurement。

**建议**：用 v1.2.1 对全部 archived artifacts 重算，重生成 abstract、Figure 3、Table 9、Conclusion 及所有百分比。v1.2 数字可留作 sensitivity appendix，不能继续充当主结果。由于不需要重新调用模型，这应是优先级最高、成本较低的实验修正。

### [P2-RIGOR-002] 91.5% 是收到 usable response 后的条件正确率

**位置**：`sections/agent_evaluation.tex:61-76`，`main.tex:74-79`。

**复算**：

```text
response availability                  = 47 / 60 = 78.3%
normalized correctness | usable        = 43 / 47 = 91.5%
normalized planned-case success        = 43 / 60 = 71.7%
unmodified correctness | usable        = 19 / 47 = 40.4%
unmodified planned-case success        = 19 / 60 = 31.7%
```

13 个排除项全部来自 Llama 3.3 70B timeout。作者正确地没有把基础设施失败伪装成 semantic error；问题是标题强调 “on your own computer” 时，部署者实际观察到的 availability 本身就是结果。

**建议替换结构**：每次出现 43/47 时并列写出三种 estimand：availability、conditional correctness、planned-case success，并明确最后一个把 serving 与 semantic failures 合并。Figure 3 可以在每个 model 下增加 planned/evaluable 两行 denominator。

### [P2-RIGOR-003] 47 个 unit 的底层任务覆盖只有四个 workflow family

**位置**：`sections/agent_evaluation.tex:14-18, 61-76`。

20 个 valid requests 是四个 workflow family × 每类五个 paraphrases，然后再与模型组合。当前 32 个 fail→pass 可能来自同一种 deterministic correction 在相近 paraphrases 上重复命中；aggregate table 看不出 family concentration。

**建议新增**：

- `model × workflow-family × condition` 结果表；
- 每个 family 的 B→C transition counts；
- leave-one-family-out sensitivity；
- 若给 uncertainty，按 workflow family 而非 paraphrase 做 cluster resampling。

这不要求把固定测试集伪装成随机总体；它回答更基本的问题：效果是否跨 family 存在。

### [P3-DEF-001] 相邻系统的 novelty 边界仍停留在叙述

**位置**：`main.tex:185-200`。

稿件引用了 FERMIACC、MadAgents、HEPTAPOD、DarkAgents，覆盖很新且基本准确；但最近邻 HEPTAPOD 自身也主张 schema-validated operations、structured/auditable layer 和 human-in-the-loop。当前 “The focus here is different” 没有被拆成可核对差异。

**建议**：增加带 primary citations 的 capability matrix，至少比较：model authority、native artifact author、shell execution、local/offline、validation boundary、clarification、audit trail、supported tools、empirical protocol。然后用一句可证伪的话定义增量，例如：

> Unlike prior HEP orchestration frameworks, HEPLocalAgent restricts the model to a typed interpretation layer and deterministically constructs every executable HEP artifact; this work evaluates that separation with same-response replay against an external scorer.

若最近邻公开可运行，最好补一个共同 MadGraph request 的小型对照；否则明确解释为何不能公平比较。

## 📝 次要修改（minor / nit）

### [P2-RIGOR-004] Severity labels 没有 rubric

`appendices/detailed_evaluation_results.tex:55-56` 称 57 个 false acceptances 中 9 low、48 moderate、0 high/critical，但全文没有 severity definition、annotator procedure 或 case-level mapping；正文又说 17 个 case 改变了 explicit scientific intent。

**建议**：给完整 rubric 与逐例 labels，或删除 severity 句，只保留更可复核的 failure mechanism 与 intent-change counts。

### [P1-CLAIM-001] 将两次重复的 0.3% 差异写成“反映 MC 统计涨落”过强

**复算**：`|844.3-841.7|/843.0=0.3084%`；`|505.7-504.1|/504.9=0.3169%`。数据与 MC variation 相容，但每个 process 只有两次重复且没有逐次 integration error。

**建议替换**：

> The repeats used independent random seeds, and the observed 0.3% differences are consistent with Monte Carlo statistical variation; with two repeats per process, this check is not designed to isolate all sources of runtime variation.

### [P4-PRES-001] Appendix C 第 21 页下半页大面积空白

`appendices/planner_selection_latency.tex:17,39` 连续使用 `[H]`，Table 7 后约半页空白，Figure 5 被推到第 22 页。把一个或两个 float 改为 `[tbp]`，或把解释段移到 Figure 5 前，再视觉复核即可。

### [P4-PRES-002] 两张 appendix 表未被编号引用

在 request collection 与 coverage 段落补 `Table~\ref{tab:eval-families}` 和 `Table~\ref{tab:eval-coverage}`。

### [P0-SURF-001] `tabularx` 重复加载

删除 `main.tex:4` 或 `main.tex:14` 中任一行。

## ✅ 已通过的关键检查

- **构建健康**：Tectonic clean exit；24 页；0 LaTeX errors；0 undefined refs/cites；0 overfull hbox >5pt；无空页。
- **headline 算术**：`7/47=14.9%`、`19/47=40.4%`、`11/47=23.4%`、`43/47=91.5%` 均正确。
- **paired transition 闭合**：`4+32+11+0=47`；Table 9 各 model transitions 与 first/full pass counts 一致。
- **boundary 计数闭合**：`39 stopped + 57 reached approval = 96`；`16+15+11+8+4+3=57`。
- **coverage 闭合**：extended evaluation `62 valid + 96 should-not-proceed = 158 usable`；planned 160，与两次无 usable response 一致。
- **ready denominator 有解释**：Table 9 的 Qwen3 `N=20` 但 `0/19 ready-but-incorrect` 不是矛盾；正文说明一个 scorer-pass 被 agent 的 output-name check 阻止，因此 overall ready denominator 为 46。
- **限制披露**：明确承认 no OS sandbox、human approval 未测、repair 基本未触发、MadAnalysis routing 0/2、builder/scorer mismatch、non-random fixed test set。这一部分写得很诚实。
- **视觉呈现**：五张主图/图表整体清楚。Figure 2 自动 text estimator 报 0.48pt 是图标/细线误判；最终页人工检查可读。源位图有效 272.3dpi，若方便可改矢量或将宽度提高到至少约 1128px。
- **公开代码抽查**：commit `feeccfb` 在当前 Linux 环境以 `PYTHONPATH=src python3 -m pytest -q` 得 439/440 passed；唯一失败是 Darwin mock 路径调用 `/usr/bin/xcrun`，属于测试环境不匹配，未被当成论文反证。
- **引用与相关工作**：未发现 undefined citation；抽查 HEPTAPOD、MadAgents、FERMIACC、DarkAgents 的题目与 scope 均与原论文摘要相符。
- **AI 使用披露**：明确、可定位，且没有用模糊的 “language assistance” 掩盖 manuscript drafting。

## 被对抗验证推翻的候选

1. **“11 个数字不在所引表中” — REFUTED**：numledger 把远处的 Table 7 当成 nearest reference；这些 paired counts 实际在 Figure 3 / Table 9 闭合。
2. **“20/20 与 0/19 分母矛盾” — REFUTED**：one scorer-pass was blocked，ready denominator 合理少 1。
3. **“Figure 2 文字严重不可读” — REFUTED**：自动投影算法误把图标线条当成小字；最终尺寸人工复核通过。

这些 refutation 很重要：它们说明 deterministic collector 只能提供候选事实，不能替代上下文判断。

## 修订优先级

1. 统一并发布可安装的 release identity。
2. 用 v1.2.1 重算全部 scorer 结果并传播数字。
3. 同时报告 availability / conditional correctness / planned-case success。
4. 增加 per-family 与 leave-one-family-out 分析。
5. 用 capability matrix 钉死 novelty 边界。
6. 给 severity rubric，或删除 severity 安慰性标签。
7. 降低 MC variation 因果措辞，修 appendix float 与两个 orphan table refs。

## 审稿人模拟（P5 — 预测，非事实）

> 以下为语言模型模拟，与真实审稿分数的相关性未经验证。用途是给 weakness 排序，不是预测录用结果。

| 角色 | 最可能肯定 | 最可能追问 |
|------|------------|------------|
| AC | scope 克制、限制披露好、artifact 可查 | 与 HEPTAPOD 的增量是否足够明确 |
| 方法学 | same-response B/C replay 是好设计 | v1.2.1 未重算、clustered paraphrases、condition-on-availability |
| 实证 | 外部 scorer 与 boundary set 比纯 demo 强 | 只有 4 family、runtime 4/7、没有 closest-system comparison |
| 怀疑论者 | 57/96 false acceptance 没有被掩盖 | 为什么 17 个 scientific-intent changes 仍没有 high severity |

**分歧点**：审稿人很可能同意“deterministic layer 改善这组测试”，但会对改善幅度能否推广、与既有 HEP agent 的差异、以及本地部署的真实 availability 产生不同评价。

完整结构化 finding 见 `findings.json`；来源判断见 `authorship_assessment.json`。
