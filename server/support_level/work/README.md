# work

这里是 server 同名 case 的源码、构建现场与原始构建记录。
完整主 case 在 Windows，实际根见 ENVIRONMENT；需要的构建记录和交付项按需取回，
不把 server 路径直接传给 Windows 工具。

基本规则：

- 一个 case 一个目录，目录名统一用 `<日期-芯片-问题>`
- 不要把不同问题混进同一个 case
- 不要只留最终产物，过程也要保留

每个 case 目录至少应覆盖这些内容：

- 目标、输入版本和成功判据
- 关键执行步骤和中间结论
- server 命令输出、构建日志等原始记录；串口和板级日志保存在 Windows 主 case
- 生成的产物、补丁、脚本、配置和交接材料

推荐最小结构：

- `README.md`：case 概要、输入、关键步骤、结论、交付项索引
- `records/`：过程记录、步骤笔记、命令线索
- `logs/`：server 命令输出和构建日志
- `artifacts/`：镜像、补丁、脚本、配置、打包结果
- `state/`：构建工具生成的软件状态；板级交接和动态事实以 Windows 主 case 为准

跨阶段交接不在两端维护两份可编辑实例：

- Windows `state/handoff.yaml` 由 `compile` 生成或更新，分开记录 server 来源和 Windows 落地路径，
  对要写入的文件核对两端大小、SHA-256 后交给 `board-exec`
- Windows `state/ledger.yaml` 由 `board-exec` 维护，记录当前板级动态事实
- server 工具生成的 `software-state` 保留原格式和 Linux 路径，按需取回作为事实副本，不手改

后续客户交付从完整 Windows 主 case 组织，server 现场提供构建和源码证据，
不以此目录单独替代全部任务上下文。
