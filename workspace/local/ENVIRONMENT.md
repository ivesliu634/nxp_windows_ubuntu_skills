# 本机环境

这是当前环境可公开的配置记录，供人和 Agent 阅读，工具不直接解析此文件。
它不是其他机器可直接套用的安装清单。迁移时对照
[环境模板](../docs/porting/ENVIRONMENT.example.md)核对并修改。

Windows 相对路径以 `workspace` 为基准，不以本文件所在的 `local` 为基准。
Linux 路径只用于 server。`<资源根>` 等引用须先从本机配置取得实际值再展开，
不能把占位字符串直接交给命令或构建工具。

本机的私有补充保存在同目录 `ENVIRONMENT.private.md`，不发布。
其中的具体机器值补充本页；各自的路径基准以文件声明为准。
该补充包含原有环境记录，历史观察不能当作本次检查结果或任务授权。

## Windows

| 内容 | 位置或说明 |
|---|---|
| Agent 工作区 | 当前 `AGENTS.md` 所在的 `workspace` |
| 工作流仓库 | `..` |
| Windows 资料根 | `..\support_level` |
| RM / 原理图 | `..\support_level\SoC_material` |
| BSP 文档 | `..\support_level\linux_document` |
| 镜像入口 | `..\support_level\Image`；本机外部镜像根见私有补充，不能把 `.lnk` 当作目录 |
| BCU | `..\support_level\tools\bcu\bin\bcu.exe` |
| 串口脚本 | `..\support_level\tools\serial-console\scripts\serial_console.py` |
| UUU | `..\support_level\tools\uuu\uuu.exe` |
| cfimager | `..\support_level\tools\cfimager.exe` |
| Python | 系统 `python`；实际版本和所需依赖使用前核对 |
| 完整 case | `..\support_level\work\<任务名>` |
| server 部署源 | `..\server\support_level`，仅小文件，不是本机源码或构建环境 |

## Ubuntu server

| 内容 | 位置或说明 |
|---|---|
| SSH 别名 | `myserver`，由 Windows SSH 配置提供；认证不写入本页 |
| 执行根 / 资源根 | 见本机私有补充；不在通用规则中写死实际账户或根路径 |
| 构建工具 | `<资源根>/tools/compile-tool/compile-tool` |
| 发布校验器 | `<资源根>/tools/build-customer-release/scripts/validate_release.py` |
| 项目规则与说明 | `<资源根>/code_assets/projects`、`compile_targets`、`software_stacks` |
| 共享源码 | `<资源根>/code_assets/projects/<项目>/<仓库>`，按本次版本核对 |
| Zephyr / HMC | `<资源根>/code_assets/workspaces/zephyr-workspace`、`hmc-workspace` |
| MCUX SDK 工作区 | 实际位置见私有补充；不等于厂商 M FreeRTOS release 包 |
| case 执行现场 | `<资源根>/work/<任务名>`，与 Windows 主 case 同名 |
| M 核编译器 | `/opt/arm-gnu-toolchain-14.3.rel1-x86_64-arm-none-eabi/bin/arm-none-eabi-gcc` |
| A 核 Linux 编译器 | `/opt/arm-gnu-toolchain-14.3.rel1-x86_64-aarch64-none-linux-gnu/bin/aarch64-none-linux-gnu-gcc` |
| A 核裸机编译器 | `/opt/arm-gnu-toolchain-14.2.rel1-x86_64-aarch64-none-elf/bin/aarch64-none-elf-gcc` |

以上编译器路径来自已有配置，不是本次重新探测的安装或兼容性结论。
更换编译器时还需同步实际使用的项目 profile 与 checklist，本页不自动修改它们。

## 尚需核对的资源

- Zephyr SDK 的实际位置及支持的 target/compiler。
- 目标板与版本匹配的厂商 M FreeRTOS release 压缩包。
- 本次 SoC/revision 所需 DDR、ELE、AHAB 等固定输入。
- 当前共享源码 ref、固件来源与校验结果，以本次任务需要的记录和现场检查为准。

配置不记录当前板卡的确定状态。板型、COM、boot mode 和启动阶段必须在任务中
fresh probe；任务事实与原始证据保存在 case。
