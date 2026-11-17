# code_assets

这里保留原仓库的项目、manifest、workspace 说明及构建清单和 policy。
已准备的正式共享基线与路径见 Windows ENVIRONMENT 登记的 server 获取记录；
部署源只保存本层说明和规则，不包含实际 checkout 或这些现场记录。
现有历史任务副本不自动作为干净基线。此处的集成 workspace 不是 AI 工作区。
说明目录不是源码 checkout。需要新版本时在 server 按任务准备，
不下载源码到 Windows，也不自动搬动既有项目。

这层再分成两类：

- `projects/`
  单个 Git 源码项目或 manifest 资产，默认按长期代码基线管理
- `workspaces/`
  只有整体协同才有意义的工作区资产

当前可直接给上层的简短理解是：

- `projects/` 放单个 Git 源码项目或 manifest，回答“本地有哪些代码基线、它们各自负责哪一段”
- `workspaces/` 放需要多仓协同才能成立的集成工作区，回答“哪条对象线需要按整体 workspace 去理解”

这层只负责回答：

- 本地有哪些代码资产
- 它们分别属于单项目源码资产、manifest，还是工作区
- 它们真实放在什么位置

## 项目入口与上游

| 项目说明 | 用途 | 官方源码来源 |
|---|---|---|
| [imx-atf](projects/imx-atf/USAGE.md) | EL3 / BL31 | [nxp-imx/imx-atf](https://github.com/nxp-imx/imx-atf) |
| [imx-mkimage](projects/imx-mkimage/USAGE.md) | 启动镜像打包 | [nxp-imx/imx-mkimage](https://github.com/nxp-imx/imx-mkimage) |
| [imx-oei](projects/imx-oei/USAGE.md) | DDR / TCM OEI | [nxp-imx/imx-oei](https://github.com/nxp-imx/imx-oei) |
| [imx-optee-os](projects/imx-optee-os/USAGE.md) | OP-TEE 安全世界 | [nxp-imx/imx-optee-os](https://github.com/nxp-imx/imx-optee-os) |
| [imx-sm](projects/imx-sm/USAGE.md) | System Manager 固件 | [nxp-imx/imx-sm](https://github.com/nxp-imx/imx-sm) |
| [linux-imx](projects/linux-imx/USAGE.md) | 通用 Linux BSP | [nxp-imx/linux-imx](https://github.com/nxp-imx/linux-imx) |
| [uboot-imx](projects/uboot-imx/USAGE.md) | 通用 U-Boot | [nxp-imx/uboot-imx](https://github.com/nxp-imx/uboot-imx) |
| [meta-real-time-edge](projects/meta-real-time-edge/USAGE.md) | RTE Yocto layer、recipe 和 patch | [nxp-real-time-edge-sw/meta-real-time-edge](https://github.com/nxp-real-time-edge-sw/meta-real-time-edge) |
| [real-time-edge-linux](projects/real-time-edge-linux/USAGE.md) | RTE Linux | [nxp-real-time-edge-sw/real-time-edge-linux](https://github.com/nxp-real-time-edge-sw/real-time-edge-linux) |
| [real-time-edge-uboot](projects/real-time-edge-uboot/USAGE.md) | RTE U-Boot | [nxp-real-time-edge-sw/real-time-edge-uboot](https://github.com/nxp-real-time-edge-sw/real-time-edge-uboot) |
| [mcuxsdk-core](projects/mcuxsdk-core/USAGE.md) | MCUX 驱动与核心源码 | [nxp-mcuxpresso/mcuxsdk-core](https://github.com/nxp-mcuxpresso/mcuxsdk-core) |
| [mcuxsdk-manifests](projects/mcuxsdk-manifests/USAGE.md) | MCUX west manifest | [nxp-mcuxpresso/mcuxsdk-manifests](https://github.com/nxp-mcuxpresso/mcuxsdk-manifests) |

其他分类包括 `android` 资产入口，以及 `hmc-workspace`、`zephyr-workspace` 集成工作区。
这些入口不等于相关资源已经取得；M 核厂商发布包另见
[release_packages/m_freertos_sdk](../release_packages/m_freertos_sdk/README.md)。

源码查阅、版本切换和修改都在 server 完成。获取版本前先在 server 用
`git ls-remote --heads --tags <URL>` 核对目标 ref；已有仓库先核对状态，
需要的 ref 不在本地时按需 fetch。分支和 tag 拼写不能互相代替，
也不能把各项目的最新 ref 自动拼成同一软件线。

如果只是查代码资产位置或角色，先留在这层。
如果任务已经变成“我要编什么”，回 `../compile_targets/` 或 `compile`。

不可通过 Git 切版本的厂商发布包不放在这里，
应进入 `../release_packages/`。
