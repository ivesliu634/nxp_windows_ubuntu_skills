# Windows imx-rm

本地 RM 的目录定位、关键词检索和有界摘录工具。
沿用 [Ubuntu imx-rm 的思路](https://github.com/lbwlele-bot/nxp_ivesliu_skill/tree/02c4fbf16ee80a5c1732a080facacc855a588231/support_level/tools/imx-rm)，
当前实现只保留章节索引、确定性标题路由、指定范围文本搜索及摘录；
不实现原工具的完整 ontology、workset、OCR 或向量检索。

工具和 PDF 都在 Windows；不上传手册，不调用 server 或在线检索服务。

## 依赖和入口

Python 3.10+，依赖本机 PDFium 解析库 `pypdfium2`，不需要额外安装 `pdftotext.exe`。
它适合大 RM，避免纯 Python 解析器反复遍历上万页的开销。
从 `workspace` 执行：

```powershell
python -m pip install -r '..\support_level\tools\imx-rm\requirements.txt'
$rm = (Resolve-Path '..\support_level\tools\imx-rm\imx_rm.py').Path
python $rm --help
python $rm list --json
```

后续示例假定 `$rm` 在同一个 PowerShell 进程中已定义；不同工具调用时重新设置变量，
或传脚本的实际绝对路径。

默认只枚举 `support_level\SoC_material\<chip>\RM\*.pdf`。
可在子命令后用 `--root 'C:\actual\SoC_material'` 指定其他资料根。
同一 chip 有多份 PDF 时必须显式选文件，不按名字或日期猜最新版本。
每个目标参数也可直接传 PDF 路径：

```powershell
python $rm build 'C:\actual manuals\reference.pdf' --json
```

## 推荐查询流程

### 1. 建索引、看目录

```powershell
python $rm build imx943 --json
python $rm toc imx943 --depth 2 --limit 80 --json
python $rm toc imx943 TPM --depth 4 --limit 20 --json
```

`build all` 为本地发现的所有 PDF 建索引。其余命令缺索引时自动为选中的 PDF 建索引，
不需要每次先运行 build。`build <target> --force` 可重建索引。
没有可导航书签的 PDF 不猜章节；改用明确页码搜索或摘录。

### 2. 从关键词定位候选章节

```powershell
python $rm lookup imx943 'tpm3 ext_clk' --json
python $rm lookup imx95 'lpuart rx pad' --json
```

查询是标题和目录路径匹配，不是对整本 RM 做全文扫描或自然语言问答。
支持少量缩写，如 `clk/clock`、`ext/external`、`pad/pin`。
排序优先模块 owner 章节；显式实例名如 `TPM3` 不应匹配明确属于 `TPM6` 的标题路径。
结果包含 `matched_terms`、`primary_term` 和 `matched_by`，用于说明为什么推荐。

同名模块可能在 AON、WAKEUP 等域中各有一章；候选不等于已确认该实例归属。
继续读 chip-specific 信息，不把排序结果当成硬件结论。
章节号只能使用当前这份 PDF 返回的 `id`，不能照抄其他 RM 版本的章节号。

### 3. 摘录指定章节或 PDF 页

```powershell
python $rm extract imx943 '<section-id>' --context-pages 1 --json
python $rm extract imx943 --pages 100:102 --json
python $rm extract imx943 --pages 100 --json
```

将 `<section-id>` 替换为本次 lookup/toc 返回的 id；没有数字章节号的书签使用
`bookmark-N` 形式的 id。章节和 `--pages` 只能选一个。

页码总是 **1-based PDF 页序**，不是页脚印刷页码。
每页返回 `pdf_page`、PDF 自带的 `page_label`（若没有则为空）和文本；
不从页脚猜页码或制造统一偏移。
章节范围根据书签层级推导，保守包含下一个同级/上级章节的起始页，
避免漏掉共享边界页上的内容，因此可能带有相邻章节片段。

默认每次最多 20 页，包含 `--context-pages` 增加的页数。
超限时明确报错，缩小范围后重试；确实需要更多页时显式传 `--max-pages N`。
不会悄悄截断章节。

### 4. 只在已选范围内搜原文关键词

```powershell
python $rm search imx943 'EXT_CLK' --pages 100:110 --limit 10 --json
python $rm search imx943 'clock' --section '<section-id>' --json
```

`search` 必须指定 `--section` 或 `--pages`，不提供默认整书扫描。
按字面字符串、不区分大小写匹配，不解释正则表达式。
返回命中 PDF 页序、标签和短上下文；`total_matches` 与实际返回数量分开，
超过 `--limit` 时可以看出结果未全部展示。零命中只代表该范围没有该字符串。

## 来源、缓存和失败边界

- 查询和摘录 JSON 带有 `pdf_path`、PDF `sha256` 和 `page_count`。
  引用结论时保留这些身份及章节/PDF 页序，不只记一段无出处文本。
- 每份 PDF 旁建立 `<完整 PDF 文件名>.index\`，保存 `index.json`、
  `CONTENTS.generated.md` 和按页缓存的 `pages\*.json`。
  不修改 PDF，也不覆盖已有的人工 `CONTENTS.md`；当前实现不解析人工目录。
- 每次核对 PDF SHA-256；源文件、索引 schema 或解析库版本改变后重新生成对应缓存。
  因此即使大小和时间戳未变，也不会复用旧 PDF 的摘录。
- PDF、索引、目录和摘录都可能含非公开资料，不能提交 Git。
  根 `.gitignore` 排除了 `*.pdf.index/`，显式传入其他路径时也不要手工加入缓存。
- 损坏、不可读、缺失、歧义或无文本层明确报错，退出码为 1，stderr 保留原因。
  索引损坏可用 `build --force` 重建；页缓存损坏时只删除报错指明的生成文件再重试。
  参数用法错误退出码为 2。
- 普通文本不保证寄存器表格列关系、位图或跨栏顺序正确。图片、复杂表格、扫描页仍回原 PDF。
  基地址、DTS 和驱动实现还要经 server 查源码，不把 RM 摘录当成源码落地证明。

## 无板测试

```powershell
python -m unittest discover -s '..\support_level\tools\imx-rm' -p 'test_imx_rm.py' -v
```

测试临时生成小 PDF，不依赖或打包真实手册。实际 RM、索引和摘录不会随工具发布。
