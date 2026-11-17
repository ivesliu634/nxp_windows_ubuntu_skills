# imx-optee-os

- 当前准备的正式 ref：`lf-6.18.37-2.1.0`；commit：`99f40897dd1fc28b4c792773b167e3db629db2ff`（2026-11-10）。
- 以下操作说明复用原工作流；新 ref 的参数和依赖仍须按源码与对应 release 核对，未执行目标构建。
- 真实源码目录：`./imx-optee-os/`
- 主要链路：`OP-TEE` / `flash.bin` 上游输入
- 对外编译清单：`COMPILE_CHECKLIST.yaml`

## 受控单清单入口

复制清单到 `records/compile/imx-optee-os/compile.yaml`，填写 ref、
`PLATFORM_FLAVOR` 和 intent。compile-tool 绑定 32/64 位工具链，在隔离源码中
构建，并把本轮 `tee-raw.bin` 发布为具名 `tee` artifact；发布动作不会丢失
原始输出到 `tee.bin` 的来源关系。

## 角色

`imx-optee-os` 用来生成 OP-TEE secure world 镜像。
在当前 `flash.bin` 链路里，它通常提供：

```text
tee-raw.bin
```

对外参与 `imx-mkimage` 打包时，RTE 链路通常要求把它转换或复制为：

```text
tee.bin
```

是否需要 OP-TEE、是否必须走 `tee-raw.bin -> tee.bin`，
先由：

- `../../../software_stacks/rte.md`
- `../../../compile_targets/flashbin/README.md`

决定。

本页只负责 OP-TEE 项目自己的源码核对、构建命令形态和产物交接。

## 使用前提

进入本页前，至少先确认：

- 目标 SoC / board
- 软件栈和版本家族
- `PLATFORM` / `PLATFORM_FLAVOR`
- A-core 工具链
- 是否需要调试配置
- 最终是否作为 `flash.bin` 输入交给 `imx-mkimage`

如果任务属于 `RTE`，先读 `../../../software_stacks/rte.md`。
如果目标是完整 `flash.bin`，先从 `../../../compile_targets/flashbin/README.md`
确认完整输入集合。

## 共享源码规则

1. 先用 `git status --short --branch` 和 `git describe --tags --always --dirty` 核对当前 ref
2. 只读检查可直接在共享源码目录做
3. 要改、要编、要生成输出，复制到 `../../../work/<case>/` 再做
4. 不要在共享源码目录里长期留下构建输出

## 平台线索

本地源码的 i.MX 平台目录是：

```text
core/arch/arm/plat-imx/
```

当前源码里可见的 i.MX9 flavor 包括：

```text
mx95evk
mx943evk
```

这些来自 `core/arch/arm/plat-imx/conf.mk`。
选择 flavor 时必须按当前 SoC、板型和软件栈核对，
不要只按名字猜。

## 构建命令形态

命令形态通常是：

```bash
cd /absolute/server/support_level/work/<case>/imx-optee-os
make PLATFORM=imx PLATFORM_FLAVOR=<flavor> \
  CROSS_COMPILE=<aarch32-prefix> \
  CROSS_COMPILE64=<aarch64-prefix>
```

例如 i.MX95 flavor：

```bash
cd /absolute/server/support_level/work/<case>/imx-optee-os
make PLATFORM=imx PLATFORM_FLAVOR=mx95evk \
  CROSS_COMPILE=<aarch32-prefix> \
  CROSS_COMPILE64=<aarch64-prefix>
```

例如 i.MX943 flavor：

```bash
cd /absolute/server/support_level/work/<case>/imx-optee-os
make PLATFORM=imx PLATFORM_FLAVOR=mx943evk \
  CROSS_COMPILE=<aarch32-prefix> \
  CROSS_COMPILE64=<aarch64-prefix>
```

这些是命令形态，不是固定 case 配方。
具体工具链、debug 选项、输出目录和额外配置要按当前 case 确认。

## 产物交接

默认输出目录下常见路径为 `out/arm-plat-imx/core/tee-raw.bin`；
若当前 case 指定了输出目录，以本轮实际命令和产物记录为准。

核心产物是：

```text
tee-raw.bin
```

如果当前 `flash.bin` 链路要求 `tee.bin`，
需要在当前 case 里保留 `tee-raw.bin -> tee.bin` 的来源关系，
再把 `tee.bin` 交给当前 case 的 `imx-mkimage` 工作目录。

不要只检查 `tee.bin` 是否存在；
还要确认它确实来自本次选定源码、版本、配置和 `tee-raw.bin`。

## 不该在这里判断的事

- 不在这里决定 generic Linux 是否需要 OP-TEE
- 不在这里决定 RTE 是否必须带 OP-TEE
- 不在这里决定 `ATF` 是否要 `SPD=opteed`
- 不在这里决定完整 `flash.bin` 输入集合
- 不在这里解释 `uuu`、烧写或运行态验证

这些分别属于 `software_stacks/`、`compile_targets/flashbin/`、
server 的 `imx-atf/USAGE.md`，以及 Windows 的 `tools/uuu/` 和 `board-exec`。
