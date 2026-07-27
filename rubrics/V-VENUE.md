# V-VENUE — 会场符合性

**判据**：这个具体会场、这一年的具体规则。

**为什么单独放在最后（公理 1）**：会场规则每年都变。页数从 8 页变 9 页，
checklist 从可选变强制，匿名政策从严格双盲变 arXiv 友好。
把这些混进 P0，会让"论文正确性"与"投稿手续"纠缠在一起——
改投另一个会场时，前者全部复用，后者全部作废。

**默认 severity**：会导致 desk reject 的 = `blocker`；其余 `major`。

**采集器**：`bin/venue.py` + `venues/<venue>.yaml` 规则表

**运行方式**：`--venue neurips-2026`。不指定则跳过本 tier，
其余 tier 全部照常运行。

---

## V1. 篇幅

| ID | 检查项 |
|----|--------|
| V1.1 | 正文页数（含图表，不含参考文献/附录/checklist）≤ 上限 |
| V1.2 | 附录若有独立上限，也符合 |
| V1.3 | 参考文献是否计入正文页数（各会场不同） |
| V1.4 | 补充材料大小限制 |

**页数判定方法**：从渲染出的 PDF 中定位 References 起始页，
而非数 `.tex` 行数。需处理"参考文献与正文同页开始"的情况。

## V2. 样式完整性

| ID | 检查项 | severity |
|----|--------|----------|
| V2.1 | 使用官方 style/class 文件，且未被修改 | blocker |
| V2.2 | 页边距未被调整 | blocker |
| V2.3 | 字号未被缩小 | blocker |
| V2.4 | 行距未被压缩 | blocker |
| V2.5 | 没有用 `\vspace{-...}` 系统性压缩章节间距 | blocker |
| V2.6 | 图表字号未小于会场允许的最小值 | major |
| V2.7 | 未使用 `\small` / `\footnotesize` 排版正文 | major |

**V2.1 判定方法**：对官方 `.sty` 计算 sha256，与该会场发布版本比对。
无法联网取官方版本时，扫描文件中的 `\setlength{\textwidth}`、
`\oddsidemargin`、`\baselineskip` 等几何量赋值。

> **V2.5 在样例论文上命中**：`grep -c vspace` 结果为
> `experiment.tex:13`、`system.tex:14`、`intro.tex:4`、`conclusion.tex:2`、
> `related_work.tex:1`、`appendix.tex:1`，共 **35 处**，
> 全部是 `\vspace{-0.5em}` / `\vspace{-0.3em}` 且成对出现在 `\section` /
> `\subsection` 前后。这是系统性压缩章节间距以挤进页数上限的典型模式。
>
> NeurIPS 明文规定 "Submissions that violate the NeurIPS style (e.g., by
> decreasing margins or font sizes) or page limits may be desk rejected."
> 单个 `\vspace` 无人追究，35 个成对出现的负间距是可被识别的模式。
> 报 `blocker`。修复方式不是删掉了事——删完会超页——
> 而是先删、再测页数、再决定删内容还是缩图。

## V3. 匿名（双盲会场）

| ID | 检查项 | severity |
|----|--------|----------|
| V3.1 | style 文件未启用 `final` / `preprint` / `finalcopy` 选项 | blocker |
| V3.2 | 无作者姓名 | blocker |
| V3.3 | 无所属机构 | blocker |
| V3.4 | 无邮箱 | blocker |
| V3.5 | 无致谢（含基金号） | blocker |
| V3.6 | 无指向可识别身份的仓库/主页链接 | blocker |
| V3.7 | 自引使用第三人称（"Smith et al. showed"，非 "our previous work"） | blocker |
| V3.8 | PDF 元数据无作者信息 | major |
| V3.9 | 补充材料/代码包内无身份信息 | blocker |
| V3.10 | 图片中无水印、路径、用户名 | major |

> **V3.1 在样例论文上命中**：`main-nips.tex` 第 4 行
> `\usepackage[final]{neurips_2026}`。`final` 选项关闭匿名，
> 直接渲染出完整作者列表与机构。
>
> **V3.2–V3.4 连带命中**：`main.tex` 中有 40 位署名作者、12 个机构、
> 以及 `Contact: {jqliu,shiqiu,huaxiu}@cs.unc.edu`。
>
> **V3.6 命中**：`\metadata[Github]{\url{https://github.com/aiming-lab/AutoResearchClaw}}`。
> 该组织名可直接定位作者团队。
>
> **V3.7 风险**：`\citet{qiu2026endtoendarchitecturecolliderphysics}` 与作者
> `Shi Qiu` 同名，且正文写 "the ColliderAgent architecture we directly adopt here"。
> 措辞本身是第三人称 ✅，但同名自引在小领域内仍可能暴露身份。报 `major`。
>
> **重要前提**：以上仅在提交**双盲评审版本**时成立。若这是 camera-ready
> 或 arXiv preprint，全部不适用。CRUCIBLE 必须先确认稿件用途再报此类 finding，
> 不能默认最坏情况——这类误报的代价是用户开始不信任整个 V tier。

## V4. 必需材料

| ID | 检查项 | severity |
|----|--------|----------|
| V4.1 | Paper Checklist 已包含并填写（NeurIPS 强制） | blocker |
| V4.2 | Checklist 每项有 Yes/No/NA + 理由 | major |
| V4.3 | Checklist 的回答与论文实际内容一致 | major |
| V4.4 | Limitations 一节存在（若强制） | blocker |
| V4.5 | Broader Impact / Ethics 一节存在（若强制） | blocker |
| V4.6 | 数据/代码可得性声明 | major |
| V4.7 | 利益冲突与资助声明（若要求） | minor |

> **V4.1 在样例论文上命中**：`main.tex` 第 179–181 行——
> ```latex
> % \clearpage
> % \newpage
> % \input{checklist}
> ```
> `checklist.tex` 文件**存在且已填写 72 行**，但在主文件中被注释掉了，
> 因此**不会出现在 PDF 里**。NeurIPS 规定 "papers that do not include the
> checklist will be desk-rejected."
>
> 这是本次审查中最值得注意的一条：文件在、内容对、只差三个 `%`。
> 静态检查扫 `.tex` 目录会认为 checklist 存在；只有**编译出 PDF 再检查**
> 才能发现它不在成品里。这正是 CRUCIBLE 坚持"先渲染再审查"的理由。
>
> **V4.3 附带风险**：checklist 中若回答"报告了误差棒"而论文实际没有，
> 属于在强制声明中作不实陈述，比缺 checklist 更严重。

## V5. 提交手续

| ID | 检查项 |
|----|--------|
| V5.1 | 主文件名与提交要求一致 |
| V5.2 | 单一 PDF，无外部依赖 |
| V5.3 | 文件大小在上限内 |
| V5.4 | 字体已嵌入 |
| V5.5 | PDF 版本兼容 |
| V5.6 | 补充材料打包格式正确 |
| V5.7 | 若有多个候选主文件，确认投的是哪一个 |

> **V5.7 在样例论文上命中**：仓库同时存在 `main.tex`（`\documentclass{fairmeta}`，
> 一个非官方模板）与 `main-nips.tex`（`\documentclass{article}` +
> `\usepackage[final]{neurips_2026}`）。两者内容大体相同但格式不同。
> 投错文件 = 用错模板 = desk reject。报 `blocker`，
> 要求在仓库中明确标注哪个是提交版本。

---

## 会场规则数据格式

规则不写死在代码里，写在 `venues/<slug>.yaml`：

```yaml
slug: neurips-2026
name: NeurIPS 2026 (Main Track)
content_pages: 9
counts_toward_limit: [main_text, figures, tables]
excluded_from_limit: [references, acknowledgments, checklist, appendix]
double_blind: true
forbidden_class_options: [final, preprint, finalcopy]
required_style_file: neurips_2026.sty
checklist_required: true
limitations_required: true
broader_impact_required: true
desk_reject_on: [page_limit, style_modification, missing_checklist, deanonymization]
source: https://neurips.cc/Conferences/2026/MainTrackHandbook
verified_on: 2026-07-27
```

`verified_on` 字段是刻意设计的：规则会过期。超过 6 个月未核实的 profile，
CRUCIBLE 会在报告顶部提示"该会场规则最后核实于 X，请对照官网复核"，
而不是假装自己知道今年的规则。
