# Vero 来源历史记录

下文保留 2026-09-28 的原始来源与检查范围，不是当前目录布局或技能安装清单。
当前入口为 [AGENTS.md](../AGENTS.md)，当前技能复用来源见资料包根 README。

本版于 2026-09-28 依据用户要求整理。

## 内容来源

原始目录位于制作电脑的 `D:/AI_test/nxp_ives_skill/`，仅作为来源记录；新包运行不依赖它们。

| 来源目录与文件 | 吸收内容 |
|---|---|
| `nxp_ivesliu_skill-main/support_level/code_assets/projects/*/USAGE.md`、相关 `COMPILE_PROFILE.yaml` | 模块用途、源码 URL、配置入口、原生命令、产物位置；改写为本版 MODULE.md |
| 同源 `software_stacks/rte.md`、`toolchain/README.md`、`firmware/README.md` | RTE 版本关系、工具链区分、固件选择经验 |
| 同源 `release_packages/m_freertos_sdk/README.md`、`PACKAGES.yaml` | 发布 SDK 与源码库的区分、包名和核角色线索 |
| `vero/.verorules/skills/support-level/SKILL.md` | Windows 原理图/RM/Image 分类、旧资源根、server 目录 |
| `vero/.verorules/skills/myserver/SKILL.md` | SSH 别名、已验证的直接 SSH / SCP 操作方式 |
| `vero_release/.verorules/skills/bcu` | Windows BCU、下载/自检脚本、B1 板级历史记录 |
| `vero_release/.verorules/skills/serial-console` | 串口工具、依赖、profile、设计说明 |

串口工具采用前一轮草案已修正的两个脚本：等待读取线程实际就绪才报告 READY；自检的导入失败和非映射 YAML 不再误报成功。其余工具来源及 profile 证据保留。
BCU/serial 的入口说明已重新压缩；BCU 的“固定占 if01”收敛到已知 B1 证据。未重新编译 BCU。

补齐并在制作时查看了官方仓库入口：[linux-imx](https://github.com/nxp-imx/linux-imx)、[RTE Linux](https://github.com/nxp-real-time-edge-sw/real-time-edge-linux)、[RTE layer](https://github.com/nxp-real-time-edge-sw/meta-real-time-edge)、[mcuxsdk-core](https://github.com/nxp-mcuxpresso/mcuxsdk-core)、[mcuxsdk-manifests](https://github.com/nxp-mcuxpresso/mcuxsdk-manifests)。具体 release/ref 仍由任务选择。

## 适用范围

本版侧重文档、目录和直接命令，保留 6 个按需加载的技能。没有移入 Ubuntu 自动构建 harness、compile-tool、自定义通信服务或强制交接状态文件。
用户提供的旧材料中，部分文档描述了原机器的资产；本地快照并未附带这些源码、PDF、SDK、工具链和镜像。因此新说明将其列为来源/目录约定，不宣称已打包。

## 检查记录

本机检查通过：Markdown 相对链接无断链；6 个技能通过随旧 Vero 提供的加载格式检查；BCU version / 支持型号列表自检通过；串口脚本导入与 4 个 profile 的无板自检通过。
没有连接目标 server、操作实物板、执行目标工程编译或验证目标电脑的 Vero 自动加载。MODULE 命令是有来源的操作模板，实际执行前需代入真实路径和版本参数。
