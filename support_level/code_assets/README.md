# 源码来源与模块索引

本目录放说明，实际 clone、搜索、修改在 server。优先使用 ENVIRONMENT 登记的当前共享基线；历史任务副本不自动作为干净基线。
每个模块说明给出仓库、常查位置、版本线索和需要时的普通构建命令。
这里由旧 `source_code` 说明目录迁入，沿用 GitHub 的 `code_assets` 分类名称；
不是本地源码仓库，也不表示 server 上的既有目录已经改名。
原 GitHub 项目 `USAGE.md`、清单、profile 与 policy 已在 server 资源目录保留；
实际构建优先使用这些服务器端说明。本地 MODULE 是旧 Vero 查找线索，不替代原项目规则。

| 需求 | 模块 |
|---|---|
| Linux 驱动、设备树、内核 | [linux-imx](linux-imx/MODULE.md) |
| U-Boot、SPL、启动环境、bootloader 设备树 | [uboot-imx](uboot-imx/MODULE.md) |
| EL3 / BL31 | [imx-atf](imx-atf/MODULE.md) |
| System Manager / M33 管理固件 | [imx-sm](imx-sm/MODULE.md) |
| DDR / TCM OEI | [imx-oei](imx-oei/MODULE.md) |
| OP-TEE 安全世界 | [imx-optee-os](imx-optee-os/MODULE.md) |
| 组合已有启动组件成 flash.bin | [imx-mkimage](imx-mkimage/MODULE.md) |
| Real-Time Edge kernel | [real-time-edge-linux](real-time-edge-linux/MODULE.md) |
| Real-Time Edge U-Boot | [real-time-edge-uboot](real-time-edge-uboot/MODULE.md) |
| RTE Yocto layer、recipe、patch 来源 | [meta-real-time-edge](meta-real-time-edge/MODULE.md) |
| M 核驱动源码与 manifest | [mcuxsdk](mcuxsdk/MODULE.md) |
| 可构建的板级 SDK 发布包 | [m_freertos_sdk](m_freertos_sdk/MODULE.md) |

服务器访问与收发文件见 [myserver](../../workspace/.agents/skills/myserver/SKILL.md)；
构建对象与交接见 [compile](../../workspace/.agents/skills/compile/SKILL.md)。
跨模块选择先看 [版本和工具链](VERSIONS.md)。具体模块可独立使用，无需先准备其他所有模块。

## 版本的用法

MODULE 中列出的版本来自用户给的 Ubuntu 资料，属于查找线索，未声明它们是一套兼容组合。
各模块分支名称可能不同；按本次 LF / RTE release note 对应表、SDK 文档和仓库 ref 选择，不默认追最新 master。
下载前可在 server 用 `git ls-remote --heads --tags <URL>` 检查目标 ref；已存在的仓库先核对当前版本。
