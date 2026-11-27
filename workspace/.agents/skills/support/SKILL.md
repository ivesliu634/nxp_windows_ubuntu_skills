---
name: support
description: 定位 NXP 工作区的资料、镜像、工具、源码、SDK、toolchain、firmware 和已有 case。适用于资源位置不明、需要确认目录用途或查找对应项目/工具说明的任务。
---

# 资源定位

## 查找方法

1. 已知目标时直接读取对应说明；位置不明时，按执行位置查资源索引：
   - [Windows 资源](../../../../support_level/README.md)：资料、镜像、板级知识、工具和完整 case。
   - [server 资源分类](../../../../server/support_level/README.md)：源码、SDK、工具链、固件和构建现场。
2. 实际路径见 [本机环境配置](../../../local/ENVIRONMENT.md)。Windows 的 `server/support_level`
   是维护/部署源，不是已下载的业务源码；源码、项目版本和远端资源现状通过 SSH 核对。
3. 只读取本次对象的 README / USAGE。已有 `RELATION.yaml` 可帮助定位关联资源和稳定 warning，
   但目录、说明或索引存在不代表资源已安装，也不代表当前实物已连接。
4. 返回已确认的位置、版本/来源、相关说明和缺失条件；找不到时明确报告，不复制整套目录补占位。

## 区分资源类型

- `code_assets/projects`：可切换 ref 的单项目源码或 manifest；不在共享源码基线中直接构建。
- `code_assets/workspaces`：协同工作区；其内含 `zephyr` 或 `mcuxsdk` 不代表应从该子目录开始编译。
- `release_packages`：不可用 Git checkout 切版本的厂商包；现有 SDK 工作区不能冒充对应 release 包。
- `software_stacks`：RTE 等跨项目软件线的版本、来源和组合关系。
- `compile_targets`：编译对象与依赖说明，不是业务源码。
- `toolchain` / `firmware`：工具链与固定二进制；路径、包名和目录存在不证明版本兼容或输入已核验。
- Windows 镜像索引、板卡历史资料与当前输入、当前实物状态分开看待。

具体资源清单只在上述目录说明中维护，不在本技能复制安装清单或默认版本。

## 查阅 i.MX RM

对 `i.MX` RM 内容类问题，按 Windows
[imx-rm USAGE](../../../../support_level/tools/imx-rm/USAGE.md)
用 `list` 确认 PDF，`toc` / `lookup` 定位候选章节，再用 `extract` 抽取有界证据。
需要原文关键词时，用 `search` 显式指定章节或 PDF 页范围，不默认扫描整本手册。
本实现不提供上游完整的 `workset`，不调用不存在的 Linux 程序。
引用时保留 PDF 路径、SHA-256、章节及 1-based PDF 页序；原始 PDF 仍是权威来源。

以下情况直接回到原始 PDF：

- `imx-rm` 找不到对应 RM
- 索引构建或章节抽取失败
- 工具结果明显缺章节或误路由
- 问题需要确认 PDF 版面、图、复杂表格
- 用户明确要求直接查原始 PDF

`imx-rm` 在 Windows 运行，PDF 及索引/摘录缓存不上传 server 或公开 Git。

## 查找已有 case

在 Windows `..\support_level\work\<case>` 查找任务说明、原始日志、产物与已有状态；
server 同名 case 是源码和构建现场，两端路径分开记录。
历史任务副本以本机配置登记的位置为准，不擅自移动。

只报告实际存在的 `README.md`、`logs/`、`artifacts/` 和 `state/`。
缺少记录时明确说明；不为纯资源查询创建状态文件，也不根据历史日志推断当前板状态。
待归纳知识位于 Windows `..\support_level\to_absorb`，保留来源 case。
