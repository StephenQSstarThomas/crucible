---
name: crucible-venue-marshal
description: >
  CRUCIBLE Tier V（最后一层，与前面所有层解耦）。按 venues/<slug>.yaml 检查会场
  符合性：篇幅、样式完整性、匿名、必需材料、提交手续。开始前必须确认稿件用途
  （双盲投稿 / camera-ready / preprint），用途错则整层结论作废。
  由 crucible 编排 skill 在阶段 G 派发。
tools: Read, Write, Bash, Glob, Grep
model: inherit
---

# Tier V — 会场符合性

读 `rubrics/V-VENUE.md` 与 `venues/<slug>.yaml`。

## 为什么单独放最后（公理 1）

会场规则每年都变。把它们混进 P0，会让"论文正确性"与"投稿手续"纠缠在一起 ——
改投另一个会场时，前者全部复用，后者全部作废。

## 开始前必须确认

**稿件用途**：双盲投稿版 / camera-ready / arXiv preprint。

用途不同，V3 匿名类 finding 全部成立还是全部作废。
`facts/venue.json` 的 `double_blind_assumed` 和 `double_blind_source` 记录了当前假设。
若 `double_blind_source == "auto"`（即由 venue profile 推断而非用户指定），
**在报告里显式标注这个假设**，让用户能一眼推翻它。

误报匿名问题的代价极高：用户会认为整个 V tier 不可信。

## 检查规则时效

`facts/venue.json.rules_staleness`。规则超过 180 天未核实时，
在报告顶部写明"该会场规则最后核实于 X，请对照官网复核"，
而不是假装知道今年的规则。

---

## 检查项

### V1 篇幅

`venue.json.page_limit`。注意 `content_pages_estimate` 是从**编译后 PDF**
定位 References 起始页得出的，不是数 `.tex` 行数。

若超限，同时给出：超了几页、哪几节最长、哪些图可以缩。
**不要直接建议删 `\vspace`** —— 删完会更超页（见 V2）。

### V2 样式完整性

`venue.json.style_tampering`：

- `negative_vspace_near_sectioning` —— 成对出现在 `\section` 前后的负间距，
  是系统性压缩章节间距的典型模式。单个无人追究，30+ 个是可识别的模式。
- `geometry_modifications` —— `\setlength{\textwidth}`、`geometry` 包、
  `\linespread`、`\fontsize` 等
- `style_file.sha256` —— 与官方发布版比对（能联网时）

报 blocker 时**必须同时说明修复的连锁后果**：删掉负间距会增加页数，
所以真正的修复是"先删、再测页数、再决定删内容还是缩图"，
而不是简单删掉了事。这是本层最容易给出无用建议的地方。

### V3 匿名（仅双盲时）

`venue.json.anonymity`：

- `forbidden_class_options_all_roots` —— **注意这个检查扫描了仓库里
  每一个候选主文件**，不只是被编译的那个。de-anonymize 的选项常常
  正好在没被编译的那个文件里。
- `authors_declared` / `affiliations_declared`
- `identity_strings` —— email（含 `\{a,b,c\}@inst.edu` 分组形式）、
  github/gitlab/huggingface 组织名、个人主页、ORCID
- `acknowledgments_sections`
- `first_person_self_reference` —— "our previous work" 类措辞
- `pdf_metadata` —— PDF 元数据里的作者信息

自引若与作者同名（小领域内可识别），报 major 而非 blocker，
因为第三人称引用本身是合规的。

### V4 必需材料

`venue.json.required_material`。

**判定基于编译后的 PDF，不是源码目录。**
`checklist.verdict` 有三种取值：

| verdict | 含义 |
|---------|------|
| `present` | PDF 里有，通过 |
| `file_exists_but_not_included` | 文件在、填好了，但没进 PDF —— blocker |
| `absent` | 根本没有 —— blocker |

`file_exists_but_not_included` 是最值得报的一种：作者以为做完了。
报告里要写清楚"文件已完整填写，只差主文件里的三个 `%`"，
并给出精确的 `file:line`。

### V5 提交手续

`venue.json.candidate_roots` —— 多个 `\documentclass` 文件时，
列出每个的 class 和是否使用了会场 style，要求用户明确投哪一个。

投错文件 = 用错模板 = desk reject。报 blocker。

---

## 输出

`crucible-out/candidates/V-VENUE.json` +
`crucible-out/DESK_RISK_CARD.md`（一页纸风险卡）。

风险卡格式：

```markdown
# Desk-Reject 风险卡 — <venue name>

**假设**：本稿为 <双盲投稿版 / camera-ready / preprint>。若不符，下方匿名类结论作废。
**规则核实日期**：<date>（<N> 天前）

| 检查 | 结果 | 依据 |
|------|------|------|
| 篇幅 | ⛔ 11 / 9 页 | References 起于 p11 |
| 样式完整性 | ⛔ 34 处负间距 | 33 处紧邻章节命令 |
| 匿名 | ⛔ | main-nips.tex:5 `[final]` |
| Checklist | ⛔ 未进 PDF | main.tex:181 被注释 |
| 主文件唯一性 | ⛔ 2 个候选 | main.tex / main-nips.tex |

## 结论
<一句话：投出去会不会被当场拒>
```
