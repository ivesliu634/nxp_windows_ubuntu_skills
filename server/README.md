# server 部署源

本目录在 Windows 工作流 Git 中维护，只保存供 Ubuntu server 使用的工具、
项目说明、清单、profile 和 policy。它不是第二个 AI 工作区，
也不是 Windows 上已经可用的源码或构建环境。

业务源码、west 工作区、SDK、固定固件、工具链实体和 case 执行现场只在 server，
不放进本目录。资料中带日期的 ref、SHA 和旧版本观察是来源记录，
不能作为新机器已经取得资源或完成构建的证明。

## 部署范围

将本目录的 `support_level` 内容对应到 Windows ENVIRONMENT 登记的
server 资源根，保留这一级目录结构：

| Windows 维护位置 | server 执行位置 |
|---|---|
| `server/support_level/tools` | `<server-resource-root>/tools` |
| `server/support_level/code_assets` | `<server-resource-root>/code_assets` |
| `server/support_level/compile_targets` 等规则目录 | `<server-resource-root>` 下对应目录 |

不要部署 Windows 的 `workspace`、`.github` 或板级 `support_level`，
也不要把外层 `server` 目录再套进远端资源根。
访问和传输方式沿用 [myserver](../workspace/.agents/skills/myserver/SKILL.md)。

1. 更新已有环境前先比较目标文件，保留远端人工修改；不要整树覆盖或使用删除式同步。
2. 只通过 SCP 传本次新增或变更的小文件，必要时保留副本；不下载业务源码到 Windows。
3. 保留 UTF-8 和 LF，尤其是 Python 入口与 Linux shell 示例。
   若通过打包部署丢失可执行权限，在 server 执行
   `chmod +x <server-resource-root>/tools/compile-tool/compile-tool`；
   也可始终用 `python3 <server-resource-root>/tools/compile-tool/compile-tool` 调用。
4. 比较两端 SHA-256，确认工具和规则一致，再查看 `compile-tool --version`、
   客户包校验器 `--help`。这些检查不启动实际构建。
5. `/opt` 编译器路径是当前配置值，不随文件部署安装。换机器时核对实际编译器，
   同步修改对应 profile 与 checklist，缺项明确报告，不靠软链接绕过路径守卫。

客户包校验脚本沿用 Windows
[build-customer-release](../workspace/.agents/skills/build-customer-release/SKILL.md)
内的实现；其 `scripts/validate_release.py` 和测试修改后，应同步到本部署源的
`support_level/tools/build-customer-release/scripts`，并检查内容一致。
server 只执行这个工具副本，不部署整个 skill。

没有常驻同步服务，也不因更新部署文件自动下载资源、编译、烧写或提交 Git。
