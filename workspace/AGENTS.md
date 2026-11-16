# NXP Windows + Ubuntu Server 工作区

用中文交流。本目录是 Windows 上唯一的 Copilot 控制层，不放业务源码。
复用 [Ubuntu 参考系统](https://github.com/lbwlele-bot/nxp_ivesliu_skill) 的技能分层和任务方法，
把源码与构建留在 server，把资料和真实板级操作放在 Windows。

## 开工与路由

1. 每个会话先读本机 [ENVIRONMENT.md](ENVIRONMENT.md)，不要输出其中的凭据。
2. 进入 [understanding](.agents/skills/understanding/SKILL.md)，按当前 unresolved step 推进，
   不预设每次都要走完整链路。
3. 只读取当前步骤需要的技能和下层说明：

| 当前问题 | 入口 |
|---|---|
| 问题理解、证据边界、方案方向 | [understanding](.agents/skills/understanding/SKILL.md) |
| 找资料、镜像、源码位置、SDK、工具或 case | [support](.agents/skills/support/SKILL.md) |
| 通过 SSH 查代码、修改、执行 Linux 命令、SCP | [myserver](.agents/skills/myserver/SKILL.md) |
| 构建对象、依赖、服务器构建和产物交接 | [compile](.agents/skills/compile/SKILL.md) |
| Windows 认板、板控、烧写、串口和运行验证 | [board-exec](.agents/skills/board-exec/SKILL.md) |
| 客户补丁、文档和 release 包 | [build-customer-release](.agents/skills/build-customer-release/SKILL.md) |

技能位于本目录的 `.agents/skills/<name>/SKILL.md`。未自动发现时，直接读取对应入口，
不依赖 Vero 或 `.verorules`。本目录是 `workspace`，同级的 `../support_level`
是资源层；从本目录执行 PowerShell 时用 `..\support_level` 或资源的实际绝对路径。

## 执行位置

| Windows | Ubuntu server，经 `ssh myserver` |
|---|---|
| RM、原理图、BSP 文档、现成镜像 | 业务 Git 仓库、源码、源码搜索和修改 |
| Windows BCU、UUU、串口及 USB 检查 | SDK、工具链、固定固件、项目原生构建 |
| 完整 case、取回的产物、板级原始日志 | 同名 case 的源码修改和构建现场 |

- 本工作流和 skills 的 Git 仓库在 Windows 维护；AI 也只在 Windows 运行。
  server 不部署 `workspace`、`.agents`、`.github` 或本工作流的 Git 仓库。
- 资料包根的 [server](../server/README.md) 是远端工具和构建规则的维护/部署源，
  不含业务源码或资源实体。不能在 Windows 运行它来替代 server，也不因此在远端部署整套工作流。
- 业务源码的 Git 仓库只放 server；Windows 不 clone 业务源码，不取回整棵源码或编译缓存。
- 板级知识、BCU/串口/UUU、RM/镜像资料和 `to_absorb` 只在 Windows；
  server 不留这些工具或资料占位目录的副本，构建产物仍可保存在 server case 中。
- 查代码直接 SSH 到 server。需要获取新版本时也在 server 完成。
- 修改前查看已有改动。共享参考基线与任务修改、构建现场分开，保留用户改动。
- 使用项目自身的 make/cmake/west 等构建方法；Agent 的真实编译统一通过 server 已部署的
  `compile-tool prepare → 展示 → run` 执行。工具链优先复用 ENVIRONMENT 中已验证的 `/opt` 路径。
- 不增加常驻通信桥、调度服务或全局强制状态表。
- 每次 SSH 是新 shell，工作目录和环境变量必须在同一次调用中设置。
- server 的路径和工具位置由 Windows 的 ENVIRONMENT 记录；不要求远端另有 AI 入口或 ENVIRONMENT。
- Windows 路径用 PowerShell 和反斜杠；Linux 路径和命令只交给 SSH 中的 Linux 解析。

## case 与两端交接

新 case 主目录为 Windows `..\support_level\work\<case>`，沿用参考系统的
`README.md`、`records/`、`logs/`、`artifacts/` 和按阶段使用的 `state/`。
server 使用同名 case 保存源码和构建现场，实际路径见 ENVIRONMENT。

- Windows 保存完整任务上下文和需要的交付项，不下载整棵源码或编译缓存。
- server 生成的构建记录、补丁、产物及相关状态按需取回主 case。
- 既有 `software-state` 仍由原构建工具生成；`compile` 负责产物交接，
  `board-exec` 负责板级观察，不因跨机器改变它们的含义。
- server 原路径与 Windows 落地路径分开记录。不要把 Windows 路径传给 Linux 工具，
  也不要把 server 路径直接传给本地 UUU。
- 取回后以文件大小、SHA-256 确认对应关系。板级操作只使用确认后的 Windows 文件。
- 原根目录的八个历史任务已按用户要求清理，不再保留第二个 `work/` 入口。
- 新发现的可复用知识先整理到 `..\support_level\to_absorb`，保留来源 case，审阅后再吸收，不自动改写历史证据。

## 板级操作与范围

保持参考系统的基准优先、证据边界和动作前后 fresh probe。
命令成功不代表整条运行链成功，历史 COM、profile 和日志不代表当前实物。
写入前确认目标板、介质和输入文件；方向改变或超出授权时先与用户对齐。

用户只要讨论、查资料、改代码或提供命令时，不自行构建、取回或上板。
已经授权的目标与动作范围内可以自主推进，不为普通步骤反复询问。
接手工作区不自动复位、切 boot mode、写 EEPROM、烧写或试编译。

## 本机数据与发布

[ENVIRONMENT.md](ENVIRONMENT.md) 是本机数据，不进入公开仓库。
凭据、内部资料、源码、镜像、SDK、固件和未经许可的工具二进制不随技能发布。
通用配置模板见 [ENVIRONMENT.example.md](docs/ENVIRONMENT.example.md)。
所有文件按 UTF-8 读取；目录重命名后以本文件所在目录为根，不写死当前文件夹名称。
