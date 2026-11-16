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

按链路粗分，当前内容大致包括：

- 启动固件链：`imx-atf`、`imx-mkimage`、`imx-oei`、`imx-optee-os`、`imx-sm`、`uboot-imx`、`real-time-edge-uboot`
- Linux BSP 链：`linux-imx`、`real-time-edge-linux`、`meta-real-time-edge`
- M 核 / SDK 代码参考链：`mcuxsdk-core`、`mcuxsdk-manifests`
- Android 资产：`android`
- 集成工作区：`hmc-workspace`、`zephyr-workspace`

如果只是查代码资产位置或角色，先留在这层。
如果任务已经变成“我要编什么”，回 `../compile_targets/` 或 `compile`。

不可通过 Git 切版本的厂商发布包不放在这里，
应进入 `../release_packages/`。
