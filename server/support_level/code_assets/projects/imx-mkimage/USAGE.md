# imx-mkimage

- 当前准备的正式 ref：`lf-6.18.37-2.1.0`；commit：`b1f801d30cf30a5d8b8dff36f8e1acafa242d53f`（2026-11-10）。
- 以下操作说明复用原工作流；新 ref 的参数和依赖仍须按源码与对应 release 核对，未执行目标构建。
- 真实源码目录：`./imx-mkimage/`
- 主要链路：`flash.bin` 打包工具
- 对外编译清单：`COMPILE_CHECKLIST.yaml`
- 内部编译 profile：`COMPILE_PROFILE.yaml`
- 项目硬门禁：`COMPILE_POLICY.yaml`

## 角色

`imx-mkimage` 是最终 boot image 打包工具。

它不负责决定整条启动固件链需要哪些输入，
也不负责决定软件栈是 generic Linux 还是 `RTE`。
这些上层判断先由：

- `../../../compile_targets/flashbin/README.md`
- `../../../software_stacks/rte.md`

完成。

本页只负责：当上层已经决定要用 `imx-mkimage` 打包时，
这个项目本身怎么核对、准备输入、运行 `soc.mak` recipe、交出产物。

## 使用前提

进入本页前，必须已经钉死：

- 目标 SoC，例如 `iMX94` / `iMX95`
- 板型、DDR 类型、必要的 SoC revision
- 软件栈和版本家族
- 最终 recipe，例如 `flash_a55` / `flash_all`
- 是否需要 `OEI=YES`
- 是否需要 `OP-TEE` 输入
- 是否需要 M 核 payload 输入
- 固定 firmware blob 来源
- 各上游输入件的来源和版本

如果这些还没确定，先回到 `compile_targets/flashbin/README.md`。
如果任务属于 `RTE`，先读 `software_stacks/rte.md`。

## 项目级受控打包入口

imx-mkimage 现在作为独立 consumer/assembler 管理：它只约束自己的源码、
参数、隔离执行、输入槽位和最终 `flash.bin`，不替 OEI、ATF、U-Boot 等
producer 定义编译方法。

`COMPILE_CHECKLIST.yaml` 复制到 `records/compile/imx-mkimage/compile.yaml`，填写
revision、SOC、recipe、producer/fixed input 选择和本轮 intent 后，
只执行 `compile-tool prepare <compile.yaml>` 和 `compile-tool run <compile.yaml>`。
原始 make 命令由 profile 生成，AI 不填写。

`COMPILE_PROFILE.yaml` 定义 `oei`、`atf`、`uboot_bin`、`uboot_spl`、`optee`、
`smfw`、`firmware` 和 `m_payload` artifact 输入槽位；M payload 允许多个，
但只能引用 M SDK 公共清单导出的 `nxp.mcore.bin`。公共清单没有裸 M 文件入口。
`oei_enabled=YES` 时必须选择 `oei` artifact，并和 consumer 的 silicon
revision 一致。

recipe 与输入以当前源码 ref 和项目说明为准，不以历史 recipe 名称表为上限。
compile-tool 读取该 ref 的 `<SOC>/soc.mak` 核对 target 并抽取 M payload 依赖；
这只是有界解析，不等于完整理解 GNU Make 的条件、include 和所有生成步骤。
Agent 仍须查阅相关源码及发布说明，明确本次完整输入和实际落位。
工具检查声明的 artifact 类型、身份、路径和 OP-TEE/ATF 关系，不替 Agent 选择业务配方。

`COMPILE_POLICY.yaml` 独立要求 make 命令显式传 `REV=<value>`，并强制所有
step 在项目自己的 `isolated_git` 副本中执行。

固定文件必须填写 `provenance`，说明实际发布包、来源及核验记录，不填手工猜测的 hash。
工具在 prepare 展示当前 SHA-256，并检查 run 消费的是同一份输入；hash 一致不自动证明
固件适配当前板型/版本，该事实由 Agent 根据当前发布资料确认。
`compile_targets/flashbin/RECIPE_CONTRACTS.yaml` 和 `FIXED_ASSETS.yaml`
保留既有组合、版本及来源参考，不再默认限制新配方、新 revision 或新发布包。
已有 case 的固定文件条目需要补充 `provenance`，更新后重新 prepare。

OEI、ATF、两条 U-Boot、OP-TEE 和 SMFW 已有独立单清单。
SCFW 尚无独立公开清单，需要已有整链路请求的场景仍可使用
`records/compile-manifest.yaml`；不与项目清单重复手填。

## 共享源码规则

1. 先用 `git status --short --branch` 和 `git describe --tags --always --dirty` 核对当前 ref
2. 只读检查可直接在共享源码目录做
3. 要改、要打包、要生成输出，复制到 `../../../work/<case>/` 再做
4. 不要把旧 `work/` 里的 `flash.bin` 直接当作当前任务产物，除非它的来源、版本、配置都已经被当前 case 重新确认

## 打包输入契约

`imx-mkimage` 消费的是已经准备好的上游输入件。
典型输入包括：

- `bl31.bin`
- `u-boot.bin`
- `u-boot-spl.bin`
- `oei-m33-ddr.bin`
- `m33_image.bin`
- `tee.bin`，仅当所选软件栈需要 `OP-TEE`
- M 核 BIN artifact，只有所选 recipe / 软件栈 / case 需要时才带入
- DDR / ELE / AHAB 等固定 firmware blob

输入集合由上层 `flashbin` 编排和软件栈决定。
不要只因为某个文件在目录里存在，就默认它应该进入本次 `flash.bin`。

项目级路径中，输入通过同 case producer manifest 的具名 artifact 引用，工具
验证 producer 成功状态、hash、type 和身份参数。它不会自动跨 manifest 执行
producer；应先完成 producer，再 assess imx-mkimage。

当前 `soc.mak + producer identity` 联合约束：

- `iMX95/flash_all` 从 `soc.mak` 得到 `m7_image.bin`，对应 producer 必须是
  `soc=imx95, core_role=m7`，固定暂存为
  `iMX95/m7_image.bin`；
- `iMX94/flash_all` 从 `soc.mak` 得到 `m33s/m70/m71` 三个文件，对应 producer
  必须是 `soc=imx943, core_role=m33s/m70/m71`，固定暂存为
  `iMX94/m33s_image.bin`、`m70_image.bin`、`m71_image.bin`；
- `iMX94/flash_all_no_m7` 只要求 `m33s_image.bin`，对应
  `soc=imx943, core_role=m33s`，不接受 CM70/CM71 payload；
- producer 文件缺失、哈希变化、SoC/core role/type 错误或传入 ELF 都会阻断。

## 常见命令形态

`i.MX943` 在 `imx-mkimage` 中通常使用 `SOC=iMX94`：

```bash
cd /absolute/server/support_level/work/<case>/imx-mkimage
make SOC=iMX94 OEI=YES LPDDR_TYPE=<lpddr4|lpddr5> flash_a55
```

需要完整 payload 集合时，recipe 可能是：

```bash
cd /absolute/server/support_level/work/<case>/imx-mkimage
make SOC=iMX94 OEI=YES LPDDR_TYPE=<lpddr4|lpddr5> flash_all
```

`i.MX95` 这类 SoC 如果 `soc.mak` recipe 要求 revision，
必须显式传入，不能猜：

```bash
cd /absolute/server/support_level/work/<case>/imx-mkimage
make SOC=iMX95 REV=<rev> OEI=YES LPDDR_TYPE=<lpddr4|lpddr5> <recipe>
```

这些只是命令形态。
具体 recipe 和参数必须以当前 SoC 的 `soc.mak`、软件栈和 case 目标为准。

## 输出与交接

核心输出通常是：

```text
flash.bin
```

`flash.bin` 属于原始 boot image。
它可以交给 `compile_targets/flashbin` 做产物归档和 handoff，
再由 `board-exec` 决定烧写、下载态、串口和运行态验证。

`imx-mkimage` 不负责证明：

- `uuu` 传输是否成功
- 板子是否已经进入 `FB`
- U-Boot 是否已经运行
- Linux 是否已经启动
- M 核运行态是否成立

这些属于 Windows 的 `board-exec`、`tools/uuu` 和本地 `board_knowledge/README.md` 索引。

## 不该在这里判断的事

- 不在这里决定 `RTE` 是否需要 `OP-TEE`
- 不在这里决定 `ATF` 是否要 `SPD=opteed`
- 不在这里决定 `SMFW` / `ATF` 是否要同步 `meta-real-time-edge` patch
- 不在这里决定 U-Boot 应该走 `uboot-imx` 还是 `real-time-edge-uboot`
- 不在这里把 `flash_a55` / `flash_all` 当成上层 compile target
- 不在这里解释 `SDPS -> FB`、second-stage `uuu` 或 FAT 运行时文件写入

这些分别属于 `software_stacks/`、`compile_targets/flashbin/`、
Windows 的 `tools/uuu/` 和 `board_knowledge/README.md`，不在 server 查找同名目录。
