# 支撑层：位置与入口

沿用 Ubuntu 参考仓库的逻辑分类，区分 Windows 资源与 server 资源。
本页不是源码安装清单，实际路径以 [workspace/ENVIRONMENT.md](../workspace/ENVIRONMENT.md) 为准。

| 分类 | 执行位置与入口 |
|---|---|
| [SoC_material](SoC_material/README.md) | Windows RM、原理图和硬件资料 |
| [linux_document](linux_document/README.md) | Windows BSP / RTE 文档 |
| [Image](Image/README.md) | Windows 镜像索引；已有镜像保留在外部实际位置 |
| [board_knowledge](board_knowledge/README.md) | 原板卡资料与历史经验；不代表当前实物状态 |
| [code_assets](code_assets/README.md) | 本地仅模块说明；查源码、修改和获取版本必须 SSH 到 server |
| [tools](tools/README.md) | Windows BCU、串口、UUU；服务器构建工具另在 server |
| [work](work/) | 新 case 的完整 Windows 主目录 |
| [to_absorb](to_absorb/) | 与 case 关联的可复用发现，审阅后再吸收 |

SDK / `release_packages`、`toolchain`、`firmware`、构建对象与源码工作区均在 server，
通过 `myserver` 定位；不为了补齐本地目录而下载源码或重资源。
远端工具和规则的小文件部署源见 [server](../server/README.md)，不与本地板级资源混用。

`code_assets` 从旧 `source_code` 的说明目录迁入；`board_knowledge` 从旧
`board_notes` 迁入，原资料内容保留。BCU 与串口工具从 `.verorules` 迁至 `tools`。
原八个历史任务已按用户要求删除，旧根目录的第二个 `work/` 入口已移除。
新 case 只使用本支撑层的 `work/`。
