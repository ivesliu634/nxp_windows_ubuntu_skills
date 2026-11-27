# 工作区移植

本文说明如何把本工作流迁移到另一套 Windows + Ubuntu server 环境，
不是 NXP 业务源码的板级移植手册，也不是完整环境备份的恢复流程。

## 1. 先分清仓库提供什么

| 仓库提供 | 需要在实际环境准备 |
|---|---|
| 工作区约定、skills、架构和操作说明 | 能发现这些入口的 Agent 客户端 |
| Windows 工具的可发布脚本、测试和说明 | Python、工具依赖、所需驱动和未附带的工具二进制 |
| server 工具、项目说明、清单和规则的维护/部署源 | Ubuntu、SSH、业务源码、SDK、工具链和固定固件 |
| 本机配置记录及环境模板 | 新机器实际路径、连接、资源版本与可用性 |

资源说明或目录存在，不代表资源已经下载或安装。
本机配置记录也不代表另一台机器具有相同路径或工具。

## 2. Windows 放置与 Agent 入口

在 Windows 获取本工作流仓库，保留 `workspace`、`support_level`、`server`
的相对关系；外层目录可以重命名。业务源码不在 Windows clone。

- [工作区说明](../../README.md)解释目录内容。
- [Copilot 指令](../../../.github/copilot-instructions.md)引用
  [AGENTS.md](../../AGENTS.md)；每次工作还要读取本机环境配置。
- skills 由 Agent 的原生机制发现并按需加载，不通过移植文档指定加载顺序。

核对所用客户端是否能发现已有指令和技能。发现失败时按该客户端的配置方法
处理，不另造调度入口，也不把 Agent、skills 或工作流仓库部署到 server。

## 3. 填写本机环境

实际配置集中在 [local](../../local/README.md)，不把机器绝对路径填进
通用约定、目录 README 或其他抽象规则描述。

仓库附带 [当前环境的可公开记录](../../local/ENVIRONMENT.md)，
应对照 [模板](ENVIRONMENT.example.md)逐项核对并修改，不能直接当作新机器配置。
若实际配置文件尚不存在，在 `workspace` 目录执行：

```powershell
$environment = '.\local\ENVIRONMENT.md'
if (Test-Path -LiteralPath $environment) {
    throw 'Existing environment: review or back up before replacing it.'
}
Copy-Item -LiteralPath '.\docs\porting\ENVIRONMENT.example.md' -Destination $environment
```

至少明确本次使用的 Windows 工具、SSH 别名、server 资源根和 case 根。
不需要的资源可以明确标记为“未安装”或“未确认”；依赖它们的任务开始前再补齐。
资源不齐不能猜默认路径、静默换版本或用历史 case 产物代替。

可公开的具体机器配置可以提交。不能公开的机器值可放在
`workspace\local\ENVIRONMENT.private.md`；该可选补充由 Git 忽略，存在时与公开配置
一并读取。声明路径基准，补充真实值，不在其中改写通用规则。
密码、token 和私钥仍由凭据存储管理，不写入任何环境模板或公开配置。

环境文件是人和 Agent 阅读的说明，不会自动配置 SSH、安装工具、部署 server，
也不是工具程序的直接配置输入。

## 4. 准备实际使用的 Windows 工具

在 `workspace` 目录先确认基础命令：

```powershell
Get-Command git, ssh, scp, python
python --version
```

按 [Windows 工具入口](../../../support_level/tools/README.md)只准备需要的工具：

- 串口脚本使用其现有 `requirements.txt`，依照
  [串口说明](../../../support_level/tools/serial-console/USAGE.md)准备 Python 依赖。
- BCU、UUU 等二进制和驱动依照各工具说明获取、安装，再记录实际位置。
  不能假定 Git 中已有可执行文件；未获再分发许可的文件不提交。
- RM、原理图、BSP 文档和镜像按资源入口自行取得，放在本机配置登记的位置。
  不为了补齐目录而复制整套资料或镜像。

工具帮助可用只证明程序可启动。迁移检查不自动写 EEPROM、复位、切 boot mode、
烧写或启动一次实际构建；有板级任务时再按授权范围核对当前实物。

## 5. 建立 SSH 与 server 资源

先在 Windows SSH 配置中建立本机环境记录的别名。沿用 `myserver` 时，
主机、账户和认证方式由使用者在自己的终端配置；仅在环境表中填写别名不会创建连接。

首次连接或排查时可执行：

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 myserver 'hostname; pwd'
```

主机指纹需核对，不能关闭校验。连接、网络和认证错误分别处理，
不把密码或私钥放进聊天、命令参数或仓库。

连接建立后核对并记录真实 server 资源根。业务源码、SDK、工具链和固定固件
在 Ubuntu 获取；资源入口见
[server 资源分类](../../../server/support_level/README.md)。
只准备任务需要的版本，不将 Windows `server` 目录当作已取得的业务资源。

共享参考源码与 case 的修改、构建现场分开。Windows 主 case 与 server 同名 case
各自使用本机配置中的根路径，不把 Linux 路径直接交给 Windows 工具。

## 6. 部署必要工具与核对构建配置

按 [server 部署说明](../../../server/README.md)只部署所需小文件：
先比较远端已有修改，再传输工具、项目说明、清单和规则，并核对 SHA-256。
不整树覆盖，不部署 `workspace`、skills 或本工作流 Git 仓库。

核对构建工具的版本或帮助入口，以及本次所需源码、编译器与固定输入。
帮助入口通过不代表依赖已经齐备。

现有项目 profile 和 checklist 可能记录固定编译器路径。改本机环境说明不会
自动改这些构建输入；迁移时按项目要求同步相关配置，不用软链接掩盖不匹配。
具体构建要求见 [compile-tool 说明](../../../server/support_level/tools/compile-tool/USAGE.md)，
迁移检查本身不执行真实构建。

## 7. 迁移完成的检查范围

- Agent 能发现工作区约定和技能，能读取当前机器的环境配置。
- 本次需要的路径不是占位值，声明的相对路径能按正确基准展开。
- Windows 工具和所需依赖可用，SSH 能访问预期 server。
- 所需远端工具部署一致，项目配置与实际源码、工具链和输入相符。
- 尚未取得或未验证的资源有明确记录。
- 发布内容已检查：可公开机器配置保留，凭据、未获许可的内部资料、重资产和完整 case 排除。

以上检查分别说明入口、资源和工具准备情况，不宣布业务构建、烧写或启动成功。
后续真实任务仍遵守 [工作区约定](../../AGENTS.md)。
