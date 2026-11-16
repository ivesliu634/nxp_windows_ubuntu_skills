# 软件版本与工具链

## LF 与 RTE

2026-11-10 准备的共享参考为 LF `lf-6.18.37-2.1.0`、RTE `Real-Time-Edge-v3.5-202607`、
MCUX `26.09.00`；Zephyr/HMC 保留正式 manifest 的配套依赖。这些是分别准备的源码线，
不是允许把各项目“最新”任意混成同一镜像。实际 ref、commit 和同步结果见本机 ENVIRONMENT 指向的记录。

Ubuntu 资料记载 RTE 3.3 对应 LF 6.12.34 家族，RTE 3.4 对应 LF 6.18.x 家族。这是历史检索线索，具体模块 ref、patch、SDK 和 firmware 按对应 release 的文档核对。

RTE 可能使用 `real-time-edge-linux` / `real-time-edge-uboot`；ATF 与 SMFW 的 patch 从相应 `meta-real-time-edge` recipe / bbappend 找。
需要 OP-TEE 的链路，ATF 通常设置 `SPD=opteed`，并将 OP-TEE 输出作为启动镜像输入。是否需要、如何配置由所选软件版本决定。
SM 的 RTE 配置可能在 `configs/other/`。不要把 RTE 所有 patch 一起套到某个模块，也不要仅凭 RTE 版本名决定 mkimage recipe。

## 编译器放 server

| 用途 | 常见 prefix / 说明 |
|---|---|
| Linux、U-Boot、ATF | `aarch64-none-linux-gnu-`，按 BSP 要求选择版本 |
| OEI、SMFW、M 核 SDK | `arm-none-eabi-`，按具体 release 要求 |
| OP-TEE | 依配置需要 32 位与 64 位工具链，查看该版本 README |
| A 核裸机 / RTOS | 可能需要 `aarch64-none-elf-`，不能沿用 Linux 配置推断 |

本机已验证 `/opt` 中 GNU 14.3.1 的 `arm-none-eabi`、`aarch64-none-linux-gnu`，以及 14.2.1 的 `aarch64-none-elf`。实际绝对路径见本机 ENVIRONMENT，不重复下载或复制工具链。
旧 Ubuntu 资料中的 9-2019-q4、其他历史工具链和 Zephyr SDK 不能仅凭目录名视为已验证。
用 server 的真实绝对 prefix，运行相应 `gcc --version` 核对；避免用通配符碰到另一个版本。

## SDK 与固定 firmware

官方 SDK 压缩包按版本保留，解到任务目录修改。普通 Git 仓库的 checkout 不能代替 SDK 换版。
DDR / ELE / AHAB 固件先在 server 的 `firmware/` 查找，核对具体 SoC、silicon revision 和文件名。
旧 vero 曾记录 `firmware-imx-8.29-8741a3b.bin`、`firmware-ele-imx-2.0.3-286c884.bin`，以及下载位置模板 `https://www.nxp.com/lgfiles/NMG/MAD/YOCTO/<文件名>`。这些只是旧版本线索，按目标 release note 确定文件和许可后获取。
一个供应商包可能含多个 SoC/revision 的 payload，文件所在父目录不能证明它适合当前板。
