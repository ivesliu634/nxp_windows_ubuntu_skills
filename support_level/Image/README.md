# Windows 镜像入口

本目录保存镜像说明，不复制已有大体积镜像。
实际镜像根见工作区 ENVIRONMENT；相邻的 `Image.lnk` 保留原 Windows 快捷方式。
PowerShell 和 Agent 不应假定快捷方式可以像目录一样 `cd`。

新任务取回的构建产物放在 Windows `support_level\work\<case>\artifacts`。
只有明确来源、版本和用途的长期资产才进入镜像存储。
修改工作区名称不应移动或删除外部镜像根。
