# P0-BUILD — 构建与渲染正确性

**判据**：稿子能不能正确变成 PDF，以及 PDF 里有没有**打开就看得见**的破绽。
这是审稿人打开文件后 5 秒内形成第一印象的地方。

**默认 severity**：编译失败 = `blocker`；渲染破绽 = `major`；排版瑕疵 = `minor`。

**采集器**：`bin/render.py`（tectonic 编译 + 日志解析 + 逐页 PNG）、`bin/refs.py`

---

## B1. 编译健康

| ID | 检查项 | 如何判定 | severity |
|----|--------|----------|----------|
| B1.1 | 主文件能在干净环境下编译 | tectonic 退出码 0 | blocker |
| B1.2 | 没有未定义控制序列 | 日志 `Undefined control sequence` | blocker |
| B1.3 | 没有缺失的宏包 | 日志 `File ... not found` | blocker |
| B1.4 | 编译不依赖本地缓存的中间文件 | 删除 `.aux/.bbl` 后重编仍成功 | major |
| B1.5 | 参考文献真的被排版出来了 | PDF 中存在 References 段且条目数 > 0 | blocker |
| B1.6 | 存在多个候选主文件时，明确哪个是投稿版本 | 目录中 >1 个含 `\documentclass` 的文件 | major |

> B1.6 不是洁癖。一个仓库里同时有 `main.tex` 和 `main-nips.tex`，
> 两者用不同的 documentclass，投错文件是真实发生过的事故。

## B2. 引用与交叉引用完整性

| ID | 检查项 | 如何判定 | severity |
|----|--------|----------|----------|
| B2.1 | 没有 `??`（未解析的 `\ref`） | PDF 文本层搜 `??` + 日志 `Reference ... undefined` | blocker |
| B2.2 | 没有 `[?]`（未解析的 `\cite`） | 日志 `Citation ... undefined` | blocker |
| B2.3 | 所有 `\cite` 的 key 在 `.bib` 中存在 | `refs.py` 差集 | blocker |
| B2.4 | 所有 `\ref` 的 target 有对应 `\label` | `refs.py` 差集 | blocker |
| B2.5 | 没有重复的 `\label` | `refs.py` 重复检测 | major |
| B2.6 | 每个 figure/table 都在正文里被 `\ref` 至少一次 | 孤儿浮动体检测 | major |
| B2.7 | `.bib` 中没有被引用的条目（膨胀参考文献） | 反向差集 | nit |

> B2.6 的意义：一个从未被正文提及的图，审稿人会问"这图是干什么的"，
> 或者更糟——认为作者在凑页数。

## B3. 渲染破绽（打开 PDF 就看得见）

| ID | 检查项 | 如何判定 | severity |
|----|--------|----------|----------|
| B3.1 | 没有文字溢出版心 | 日志 `Overfull \hbox` 且溢出量 > 5pt | major |
| B3.2 | 没有大面积空白页/半空页 | 逐页 PNG 墨水覆盖率 < 15% 且非末页 | major |
| B3.3 | 图片全部存在且渲染出来 | 日志缺图 + PNG 中无空白占位框 | blocker |
| B3.4 | 表格没有超出页宽 | 表格所在页 Overfull + 视觉检查 | major |
| B3.5 | 浮动体没有全部堆到文末 | 检测连续 >3 页纯浮动体 | major |
| B3.6 | 数学公式没有被截断/压出边界 | 长公式行的 Overfull | major |
| B3.7 | 没有断掉的连字符/奇怪的分词 | Underfull \hbox badness > 8000 | nit |
| B3.8 | 页眉页脚没有占位符残留 | PDF 文本搜 `\thepage`、`DRAFT`、`TODO`、`XXX` | major |

## B4. 稿件状态残留

| ID | 检查项 | 如何判定 | severity |
|----|--------|----------|----------|
| B4.1 | 正文没有 `TODO` / `FIXME` / `XXX` / `??` 注释外泄 | PDF 文本层搜索（注意：只查渲染出来的） | blocker |
| B4.2 | 没有 `\todo{}` / `\note{}` 类批注宏渲染出来 | 宏调用扫描 + PDF 文本 | blocker |
| B4.3 | 没有 lorem ipsum / 占位文本 | 关键词扫描 | blocker |
| B4.4 | 没有被 `\input` 但内容为空的文件 | `ingest.py` 文件大小 + 有效内容行数 | major |
| B4.5 | 没有指向已删除章节的 `\ref` | B2.4 的子集，单独报 | major |
| B4.6 | 修订标记（`\textcolor{red}`、latexdiff 残留）已清除 | 宏扫描 | major |

> B4.4 命中示例：`sections/analysis.tex` 只有两行注释、`sections/ethics.tex` 是 0 字节，
> 但 `main.tex` 仍 `\input{sections/analysis}`。编译不报错，PDF 里那一节直接消失，
> 而正文其他地方还在 `\ref` 它。

## B5. 可复现性（构建层面）

| ID | 检查项 | 如何判定 | severity |
|----|--------|----------|----------|
| B5.1 | 仓库里没有绝对路径 | `\includegraphics{/home/...}` 扫描 | major |
| B5.2 | 没有缺失的自定义 `.sty` / `.cls` | 文件存在性 | blocker |
| B5.3 | 字体不依赖本机安装 | 非标准字体宏包检测 | minor |
| B5.4 | 图片路径大小写一致（Linux 敏感） | 文件系统匹配 | major |
