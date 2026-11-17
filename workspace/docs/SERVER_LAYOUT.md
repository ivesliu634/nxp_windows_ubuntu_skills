# server 目录约定

Windows 是唯一 AI 工作区，也是本工作流与 skills 的维护位置。
server 只是资源和执行端，AI 通过 `myserver` skill 使用 SSH/SCP 操作它。
实际连接、资源根和工具路径只记录在 Windows 的 ENVIRONMENT。
Windows 资料包根的 [server](../../server/README.md) 保存工具和规则的维护/部署源，
只有其中的 `support_level` 小文件映射到下列远端资源根，不部署整套 Windows 工作区。

用户指定的 `copilot_workspace` 名称保留，但它不是需要打开的 AI 工作区：

```text
copilot_workspace/
├─ README.md                           资源端说明
└─ support_level/
   ├─ code_assets/projects/<模块>/      原项目说明、清单、profile、policy
   ├─ compile_targets/                 原构建对象说明与规则
   ├─ software_stacks/                 原软件线说明
   ├─ tools/                          仅服务器执行工具
   │  ├─ compile-tool/
   │  └─ build-customer-release/
   ├─ release_packages/                发布包入口，不表示压缩包已取得
   ├─ toolchain/                       工具链入口，实际已有路径见 ENVIRONMENT
   ├─ firmware/                        固定输入入口，版本按任务核对
   └─ work/<任务名>/                    server 源码和构建现场
```

server 不保留本工作流的 `.git`、`.github`、`workspace`、skills 或 AI 入口。
业务源码仓库自身的 `.git` 保留；`code_assets/workspaces` 是 west 等多仓源码集成目录，
不是 AI 工作区。源码、SDK、工具链与构建现场不因这次整理改名或搬动。
校验客户包需要的脚本单独部署到 `support_level/tools/build-customer-release/scripts`，
不为运行它保留整个 skill。

`board_knowledge`、`Image`、`SoC_material`、`linux_document` 和 `to_absorb` 只在 Windows，
BCU、串口、UUU 也只在 Windows。原 Ubuntu 历史板级资料已归并到 Windows 板卡资料索引，
不因清理重复目录而丢弃。`imx-rm` 只在 Windows 查询本地 PDF，
不部署到 server；server 也不部署当前无调用的 `task-tool`。
需要镜像时在 server case 生成并按需取回，不另建 Windows 专属的长期镜像资料目录。

已准备的正式源码与依赖以 server setup case 的 `records/source-inventory.json`
和 `source-validation.json` 为准；说明目录本身不能证明源码或发布包已齐备。
Windows 的 `support_level` 不再保留 `code_assets` 或重复模块说明。
源码与项目说明经 SSH 读取 server 的 `support_level/code_assets`；
Windows `server/support_level` 仅保留工具和规则的 Git 维护/部署源。

用户给了自己的可编辑 checkout 时直接使用那个目录。共享源码用于查询和准备副本，避免一次任务改变别人的源码版本。
SDK 是解包的 release，与 Git 仓库分别组织；对应 release 的 SDK 不齐时不能靠 mcuxsdk-core 近似替代。
