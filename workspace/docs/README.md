# 工作区设计文档

这里保存工作区的架构说明，以及后续确认的施工说明和设计演进记录。
读者是需要理解、维护或调整这套工作区的人；不是每次任务开始时必须读取的 Agent 入口。

## 当前文档

- [架构文档](ARCHITECTURE.md)：说明当前 Windows + Ubuntu server 的职责、资源组织、
  执行工具、case 与证据边界。当前为待逐节审阅的初稿，不代表全部设计已确认。
- 施工文档暂不编写；架构确认后再讨论如何搭建、部署和验收。

需要了解整体设计时读架构文档；需要配置机器或执行具体操作时，查相应配置模板和技能/工具说明，
不把这里的设计说明作为额外的任务执行流程。

## 原有文件的归属建议

以下文件目前仍在本目录，尚未移动或删除。建议先确认归属，再迁移有效内容、更新引用并移除重复文件。

| 文件 | 实际用途 | 建议 |
|---|---|---|
| [ENVIRONMENT.example.md](ENVIRONMENT.example.md) | 填写 Windows 与 server 实际路径的模板 | 保留，移到 `workspace\ENVIRONMENT.example.md`，与生成的本机配置相邻；不归入某一个技能，也不作为架构说明 |
| [SERVER_LAYOUT.md](SERVER_LAYOUT.md) | 服务器目录、部署边界及历史整理说明 | 整体分工由架构文档解释，部署映射归 [server/README.md](../../server/README.md)，资源目录职责归 [server 资源说明](../../server/support_level/README.md)；核对有效内容后删除这份重复说明 |
| [SERVER_OPERATIONS.md](SERVER_OPERATIONS.md) | SSH、Git、SCP 和跨 shell 命令示例 | 不保留独立操作入口；有价值的示例归 [myserver 技能](../.agents/skills/myserver/SKILL.md) 的按需参考资料，构建要求引用项目和工具说明；完成归并后删除原文件 |

配置模板与设计文档用途不同，不能仅因为都是 Markdown 就放在一起。
归并操作示例也不等于把整份文件塞进技能正文；正文保留关键规则，较长示例按需引用。

## 文档边界

- 本目录解释设计原因、职责与边界，不重复维护工具命令、资源安装清单或当前设备状态。
- 具体目录的 README 解释该目录用途；项目和工具的 USAGE 解释具体操作。
- 本机路径保存在非公开的 `workspace\ENVIRONMENT.md`；任务事实和原始证据保存在 case。
- 当前设计更新到架构文档；需要保留历史方案时再明确归档，不预先创建空的版本目录。

返回 [仓库说明](../../README.md)。
