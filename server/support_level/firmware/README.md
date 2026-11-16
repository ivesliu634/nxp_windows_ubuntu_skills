# firmware

这里放固定二进制输入。
当前 server 已保存下列正式 LF 配套的原始供应商包，尚未解包或验证具体板级输入。
另有历史 SCFW 候选，实际路径由 Windows ENVIRONMENT 记录；
具体输入以本次任务的版本和文件核对为准。
下文目录和供应商包是上游分类、历史案例，不是本机已安装清单。

它不放源码，也不放 case 里临时生成的产物。

适合放的内容包括：

- DDR firmware
- ELE / AHAB container
- vendor firmware package 解包结果
- 其它不应和 `code_assets/projects/` / `code_assets/workspaces/` 混在一起的固定输入

## 已下载的官方原始包

2026-11-16：按已取得的 `lf-6.18.37-2.1.0` 源码线，保存其官方
`meta-imx` tag `rel_imx_6.18.37_2.1.0` 指定的两个原始安装包。
server 相对本目录的位置为 `vendor_packages/lf-6.18.37-2.1.0/`：

| 原始文件 | 字节数 | SHA-256 |
|---|---:|---|
| `firmware-imx-8.33-7ce4783.bin` | 2032598 | `2b24b8c059b4c110344120635bc2b1de1b2963f894d9edd916704ee9cf1b58b8` |
| `firmware-ele-imx-2.0.7-0265375.bin` | 2495040 | `a24f0e6be783a09281d44b0c2fb26ed719038387441e7ef325b9d4c514592b1d` |

来源和校验依据：

- [firmware-imx 官方下载](https://www.nxp.com/lgfiles/NMG/MAD/YOCTO/firmware-imx-8.33-7ce4783.bin)；
  [对应 recipe 和官方 SHA-256](https://github.com/nxp-imx/meta-imx/blob/rel_imx_6.18.37_2.1.0/meta-imx-bsp/recipes-bsp/firmware-imx/firmware-imx-8.33.inc)。
- [ELE 官方下载](https://www.nxp.com/lgfiles/NMG/MAD/YOCTO/firmware-ele-imx-2.0.7-0265375.bin)；
  [对应 recipe 和官方 SHA-256](https://github.com/nxp-imx/meta-imx/blob/rel_imx_6.18.37_2.1.0/meta-imx-bsp/recipes-bsp/firmware-imx/firmware-ele-imx_2.0.7.bb)。

下载及传输后均已核对官方 SHA-256；同目录的 `SHA256SUMS` 可用于复查。
原始包只保存在 server，不进入 Windows 部署源或公开 Git。
这两个包是需确认供应商许可的自解包安装器，当前未执行、未自动接受许可；
确认许可并解包后，还需逐项核对目标 SoC、silicon revision 和 DDR 文件。

本次只补齐原始包，不表示已具备可直接打包的板级 firmware。
现有 [FIXED_ASSETS.yaml](../compile_targets/flashbin/FIXED_ASSETS.yaml)
仍绑定历史 `firmware-imx 8.29` 和 `firmware-ele-imx 2.0.3` 的具体文件哈希，
不能用这些新包静默替代，也不为通过检查改写旧哈希。

## 使用规则

1. 先确认当前任务是不是在找固定二进制输入
2. 先按 SoC 根目录找
3. 再进具体 vendor package 目录核对文件名和版本
4. 不要只因为“某个文件出现在某个包里”，就把那个包目录名当成唯一 provenance

## 当前目录模型

原仓库建议按这些 SoC 分类：

- `imx8dxl/`
- `imx943/`
- `imx95/`

每个 SoC 根下面允许保留 vendor package 的原始解包形态。
所以你看到的常常不是“一个文件一个平铺目录”，
而是：

```text
firmware/
  <soc>/
    <vendor-package>/
      ...
```

## 已吸收：`imx95-rte33-build-flashbin` 的 firmware 边界

对 `i.MX95 RTE 3.3 flash.bin`，
旧 skill 的稳定要求不是“再下载一份 firmware”，
而是先确认：

- canonical reusable root 在 `../support_level/firmware/imx95/`
- 先看本地有没有所需 vendor package
- 没有时才考虑补下载

上游案例曾使用以下供应商包，本机尚未确认取得：

- `firmware-ele-imx-2.0.3-286c884/`
- `firmware-imx-8.29-8741a3b/`

## 多 SoC payload 注意事项

vendor package 解包目录本身可能包含多颗 SoC 的 payload。

例如一个 `firmware-ele-imx-*` 目录里，
可能同时看到：

- `mx943...`
- `mx95a0...`
- `mx95b0...`

所以：

- “文件在某个 vendor package 目录里”
  不等于“它天然只属于这个 SoC 根”
- 真正 output-affecting 的，是：
  具体文件名
  具体 revision
  以及当前链路要求的 SoC / rev 身份

对 `i.MX95` 这类链路，尤其要防止：

- 把 `A0` / `B0` 混看
- 只看目录名字，不看实际文件名字
- 把错误 revision 的 blob 误判成 传输 问题

## 当前推荐读取方式

如果任务是 `flash.bin` build：

1. 先读相关源码项目 `USAGE.md`
2. 再来这里确认固定输入根目录
3. 明确记录：
   - 当前要用哪个 package
   - 当前要用哪个 SoC / rev 对应文件

如果任务是 `i.MX8DXL`，优先看：

- `validated-lf-6.18.2-1.0.0/`

如果任务是 `i.MX95 RTE 3.3`，
当前先把 `imx95/` 当成本地 canonical root，
不要再反过来把 `imx943/` 下带出来的 `mx95*` 文件当默认入口。

## 当前不该怎么用

- 不要把 `firmware/` 和 `code_assets/projects/` / `code_assets/workspaces/` 混读
- 不要在这里生成临时 build 输出
- 不要让 case 操作手册直接写死一个旧共享根路径而跳过这里
- 不要在 revision 不清楚时继续往下烧写或打包
