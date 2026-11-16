# server 工具

| 工具 | 入口 | 操作说明 |
|---|---|---|
| 编译 | `compile-tool/compile-tool` | [USAGE](compile-tool/USAGE.md) |
| 客户包校验 | `build-customer-release/scripts/validate_release.py` | [USAGE](build-customer-release/USAGE.md) |

AI 在 Windows 加载 skills，经 `myserver` skill 使用 SSH 调用这些工具。
真实编译使用 `compile-tool prepare → 展示 → run`；输入和 case 路径均是 Linux 路径。
工具可启动不代表具体任务的 SDK、固定固件或其他构建输入已齐备。

BCU、串口、UUU 和 RM 查询都在 Windows，不在 server 放副本或空工具目录。
原 `task-tool` 未被当前 skills 调用，不作为 server 运行依赖。
