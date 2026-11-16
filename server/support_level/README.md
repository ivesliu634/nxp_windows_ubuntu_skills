# support_level

这里是 server 资源与执行端，保留原 GitHub 的项目规则和构建工具，
以及按任务在 server 准备的业务源码与构建现场。AI、skills 和工作流 Git 仓库只在 Windows，
通过 `myserver` skill 使用 SSH/SCP 操作这里，不需要远端 AI 工作区。

连接和资源路径由 Windows ENVIRONMENT 记录，server 不另存 AI 配置副本。
正式基线、路径和获取校验从 Windows ENVIRONMENT 登记的 server case 记录核对；
获取记录不随部署源发布，也不能从本目录的存在推断资源已下载。
项目说明、清单和 policy 已导入，不表示源码、SDK 压缩包或固件 blob 已齐备。
现有其他任务的源码不自动迁入或视为干净 release 基线。

当前目录：

- `code_assets/`
- `compile_targets/`
- `release_packages/`
- `software_stacks/`
- `tools/`
- `toolchain/`
- `firmware/`
- `work/`

板级知识、RM/原理图、BSP 文档、长期镜像资料和 `to_absorb` 只在 Windows，
不在这里保留重复目录。BCU、串口和 UUU 也只在 Windows 执行。
原 Ubuntu 的历史板级资料已归并到 Windows 板卡资料索引，不代表当前连接的实物。

说明：

- `code_assets/` 放长期保留的代码资产，下面再分 `projects/` 和 `workspaces/`
- `compile_targets/` 放编译对象入口，由 `compile` owner
- `software_stacks/` 放跨项目的软件栈 / 软件线说明，例如 `RTE` 与 LF 家族、启动镜像内容差异
- `release_packages/` 放不可通过 Git 切版本的厂商 release 包，例如 `m_freertos_sdk` 和 `SCFW`
- `firmware/` 放 DDR firmware、AHAB 等固定二进制输入
- `tools/` 只保留 `compile-tool` 和 `build-customer-release`，各工具有自己的 USAGE
- `work/` 放同名 case 的源码、构建现场和生成记录；完整任务上下文及板级日志在 Windows
- `toolchain/`、`firmware/`、`release_packages/` 可在各自目录下补最小 README 作为入口

这里的文档主要负责：

- 这层里有什么
- 它们放在什么位置
- 该进哪一层 README 或 `USAGE.md`

文档分工：

- 每一层目录下的 `README.md` 负责说明这一层里有什么、怎么分布、该往哪一层继续走
- 每个代码项目、manifest、release 包或具体工具旁边的 `USAGE.md` / `README.md` 负责操作手册

如果目标涉及 `RTE`、`Real-Time Edge` 或其他跨项目软件线，先进入 `software_stacks/`。
如果已经明确要看某个代码项目或 manifest，再去项目目录旁边读取 `USAGE.md`。
如果目标是不可切版本的 release 包，进入 `release_packages/`。

原仓库保留的项目 / manifest 说明包括（不等于已取得源码）：

- `imx-atf`
- `imx-mkimage`
- `imx-oei`
- `imx-optee-os`
- `imx-sm`
- `linux-imx`
- `mcuxsdk-core`
- `mcuxsdk-manifests`
- `meta-real-time-edge`
- `real-time-edge-linux`
- `real-time-edge-uboot`
- `uboot-imx`
- `android`
