# CRUCIBLE

投稿前自查论文用的一组 Claude Code skill 和 subagent。

给它论文的 LaTeX 源码（Overleaf 导出的 zip、git 仓库或本地目录），它会编译 PDF、抽取正文和表格里的数字，再让多个 agent 并行审查，最后给出问题清单和按顺序排好的修改建议。

它不代写论文，也不预测能不能中，只负责在审稿人之前把能查出来的问题查出来。

Codex 版本在 [`codex/adaptation`](https://github.com/StephenQSstarThomas/crucible/tree/codex/adaptation) 分支。

## 安装

作为 plugin 安装（在 Claude Code 里执行）：

```text
/plugin marketplace add StephenQSstarThomas/crucible@claude-code
/plugin install crucible@crucible
```

装好后命令是 `/crucible:crucible`。

或者 clone 下来用脚本链接到 `~/.claude`，命令是 `/crucible`：

```bash
git clone -b claude-code https://github.com/StephenQSstarThomas/crucible.git ~/crucible
cd ~/crucible && ./install.sh            # --project 装到当前项目的 .claude/
```

两种方式都是 2 个 skill 加 17 个 subagent，装完重启 Claude Code。

依赖：`python3`、`tectonic`、`pymupdf`、`pillow`、`pyyaml`。没有 `tectonic` 时只能做源码层面的检查，页数、图表清晰度这类要看 PDF 的检查会跳过。

## 使用

```text
/crucible ~/paper.zip --venue iclr-2027 --purpose submission
/crucible ~/paper --evidence ~/paper/runs     # 提供实验日志，可以核对数字是否与记录一致
/crucible ~/paper --no-fix                    # 只出报告，不改源码
```

| 参数 | 作用 |
|------|------|
| `--venue` | 会场规则，目前有 `neurips-2026`、`iclr-2027`（见 `venues/`） |
| `--purpose` | `submission` / `camera-ready` / `preprint`，决定是否检查匿名 |
| `--evidence` | 实验产物目录 |
| `--root` | 仓库里有多个主文件时指定一个 |
| `--tiers` | 只跑部分检查，如 `P0,P1` |
| `--no-fix` / `--no-panel` | 不做自动修复 / 不跑模拟审稿 |

不经过 agent、只跑确定性采集：

```bash
python3 bin/collect.py ~/paper -o crucible-out --venue iclr-2027
```

## 输出

```
crucible-out/
├── REPORT.md           问题清单，按严重程度排序，附复算过程
├── REVISION_PLAN.md    修改建议：先改什么、改哪一行、可直接粘贴的英文替换文本、工作量
├── DESK_RISK_CARD.md   会不会被直接拒稿（给了 --venue 时）
├── findings.json       结构化结果，含被验证推翻的条目
├── panel/              四份模拟审稿意见
├── patches/            需要你确认的修改
└── facts/ preview/     采集结果、逐页渲染图
```

只有一种改法的问题（拼写、断掉的 `\input`、重复的 label）会直接修，提交到稿件仓库的 `crucible/fixes` 分支。涉及数字、结论措辞、删减内容的修改只生成补丁，由你决定。

## 流程

1. **采集**：编译、逐页渲染、解析表格和数字、测量图片的实际分辨率。脚本只记录事实，不下结论。
2. **并行审查**：7 个分层审查 agent、4 个模拟审稿人、1 个会场检查 agent 同时运行。模拟审稿人看不到其他 agent 的结果，避免互相影响。稿子较长时按章节分片。
3. **验证**：P0、P1 和会场类的每条问题都交给一个独立的 verifier 尝试推翻，P2–P4 抽查。被推翻的不进报告。
4. **修复**：机械问题最多修 3 轮，每轮重新采集并对比，确认没有改坏别的地方。
5. **汇总**：生成修改建议和写作来源判断，脚本校验报告结构。

## 检查范围

| 层级 | 内容 |
|------|------|
| P0-BUILD | 编译错误、`??`、缺图、草稿残留、空的被引文件 |
| P0-INTEG | 正文与表格数字矛盾、表内算术对不上、过期数字、不存在的引用、图片复用 |
| P0-SURF | 拼写、记号不一致、结构缺失 |
| P1-CLAIM | 每条主张有没有对应证据，每个机制有没有自己的对照实验 |
| P2-RIGOR | baseline、ablation、误差棒、选择性报告、分母是否可比 |
| P3-DEF | 问题定义是否清楚，贡献增量是否站得住 |
| P4-PRES | 图表在最终尺寸下是否看得清，caption 是否自足 |
| P5-PANEL | 模拟 AC 和三位审稿人 |
| V-VENUE | 页数、匿名、样式修改、必需材料 |

每层的完整检查项在 `rubrics/`。

报告第一节是写作来源判断，只给"人类主导 / AI深度参与 / 全AI"三档之一。依据是 AI 使用声明、源码里的生成残留、版本历史等，不根据文风判断，也不给百分比。这是风险提示，不是取证结论。

## 实际效果

这套检查最早用在一篇 NeurIPS 投稿上。那篇稿子已经改过 6 轮，常规静态检查全部通过，仍然查出：

- `checklist.tex` 已经填好，但 `main.tex` 里的 `\input{checklist}` 被注释掉了，PDF 里没有 checklist。NeurIPS 对此直接拒稿。
- 正文写 19 次干预，引用的那张表里是 6。
- 表格 Overall 列按 caption 声明的权重算不出印出来的数，反推出实际用的是另一组权重。

之后拿这篇稿子的三份真实审稿意见做了对照，19 条审稿关切中独立命中 13 条，过程和不计分的项见 [examples/VALIDATION-vs-human-reviewers.md](examples/VALIDATION-vs-human-reviewers.md)。完整报告样例见 [examples/AutoResearchClaw-REPORT.md](examples/AutoResearchClaw-REPORT.md)。

## 限制

- 没有 `--evidence` 时只会说"两个数字互相矛盾"，不会断言数据是编造的。
- 新颖性检查依赖联网检索，结果会随检索内容变化。
- 模拟审稿的分数没有校准，只用来给问题排优先级。
- 不做文风润色。

## 目录

```
skills/crucible/          编排流程
skills/crucible-report/   报告格式
agents/                   各审查角色（subagent）
.claude-plugin/           plugin 与 marketplace 清单
rubrics/                  每层检查项
bin/                      采集、合并、校验脚本
venues/                   会场规则
contracts/                finding 与来源判断的 JSON schema
CRUCIBLE.md               设计说明
```

## 开发

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
claude plugin validate .
tests/smoke.sh ~/paper.zip iclr-2027
```
