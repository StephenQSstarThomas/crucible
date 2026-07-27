# Desk-Reject 风险卡 — NeurIPS 2026 Main Track

**稿件**：AutoResearchClaw
**假设**：本稿为**双盲投稿版**。若为 camera-ready 或 arXiv preprint，下方第 4 项作废。
**编译主文件**：`main.tex`（`\documentclass{fairmeta}`，**非** NeurIPS 官方模板）
**规则核实日期**：2026-07-27（0 天前）
**来源**：neurips.cc/Conferences/2026/MainTrackHandbook

---

## 结论

**按现状提交会在进入评审前被拒。** 下列五项**各自独立**构成 desk reject 理由，
不是同一个问题的五种表现。

---

| # | 检查 | 结果 | 精确依据 |
|---|------|------|----------|
| 1 | **篇幅** | ⛔ **11 / 9 页** | References 起于 PDF 第 11 页；正文+图表共 11 页，超限 2 页 |
| 2 | **样式完整性** | ⛔ **34 处负间距** | 33 处紧邻 `\section`/`\subsection`。分布：system 14、experiment 13、intro 4、conclusion 2、related_work 1 |
| 3 | **Checklist** | ⛔ **未出现在 PDF 中** | `main.tex:181` → `% \input{checklist}`。`checklist.tex` 存在、5345 字节、**已完整填写** |
| 4 | **匿名** | ⛔ **完全暴露** | `main-nips.tex:5` → `\usepackage[final]{neurips_2026}`；36 个 `\author`、13 个机构、`\{jqliu,shiqiu,huaxiu\}@cs.unc.edu`、`github.com/aiming-lab` |
| 5 | **主文件唯一性** | ⛔ **2 个候选** | `main.tex`（fairmeta，**未**使用 neurips_2026.sty）与 `main-nips.tex`（使用了）。投错 = 用错模板 |

---

## 修复顺序（有依赖关系，不要打乱）

```
① 先确定投哪个主文件
   main.tex 用的是 fairmeta，不是 NeurIPS 模板 —— 若投它，等于用错模板。
   → 确认 main-nips.tex 为提交版本，或把 main.tex 切到官方模板。

② 去掉 [final] 选项
   main-nips.tex:5  \usepackage[final]{neurips_2026}
                 →  \usepackage{neurips_2026}
   这会自动隐藏作者块。再单独确认：致谢、GitHub 链接、PDF 元数据、
   补充材料内是否仍有身份信息。

③ 取消 checklist 的注释
   main.tex:181  % \input{checklist}  →  \input{checklist}
   然后核对 checklist 里每一项的 Justification 与论文实际内容是否相符 ——
   在强制声明中作不实陈述，比缺 checklist 更严重。
   （已知风险：Limitations 项指向 Appendix J 与失败分析附录，需确认这两处存在。）

④ 删除 34 处负间距
   ⚠️ 这一步会让页数变得更多，不要单独做。

⑤ 重新测页数，然后削减内容到 9 页以内
   当前 11 页，删完负间距预计 11.5–12 页，需要压缩约 3 页。
   可考虑：把表 8/9（附录 prompt 库、topic 列表）确认已在附录不计页数；
   案例研究图改为半栏；related work 表精简。
```

**关键点**：第 ④ 步和第 ⑤ 步必须一起做。只删负间距而不削内容，
会把一个"样式违规"变成一个"更严重的篇幅违规"。

---

## 不构成 desk reject，但同样在评审前就会被看到

- 正文写"CoPilot 用了 **19** 次干预"，它引用的表里写的是 **6**（`experiment.tex:133`）
- 表 4 的 Overall 列，作者自己的系统与两个 baseline 用了**不同的加权方案**，
  且本方法的 0.867 无法由任何一种方式复算出来（最接近的是 0.7433）
- `sections/analysis.tex` 是空壳，但 `main.tex:167` 仍在 `\input` 它

这三条在 `REPORT.md` 中有完整复算。
