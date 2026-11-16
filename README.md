# NXP Windows + Ubuntu Server

```text
workspace/       Copilot 入口、skills、本机配置和说明
support_level/   Windows 资料、工具和完整 case
server/          server 工具和构建规则的部署源，不含业务源码或运行资源
```

唯一 Agent 入口：[workspace/AGENTS.md](workspace/AGENTS.md)。
资源入口：[support_level/README.md](support_level/README.md)。
server 部署说明：[server/README.md](server/README.md)。

Windows 是唯一 AI 工作区，在这里维护本工作流及 skills，查资料、控制板子和抓串口。
业务源码仓库与构建只在 Ubuntu server，由 Windows 的 `myserver` skill 通过 SSH 操作。
server 只保留源码、SDK、工具链、构建工具、固定固件和执行现场，
不部署 AI 工作区、技能发现入口或本工作流的 Git 仓库。
`server/` 在 Windows 维护，只把所需工具和规则部署到远端，不改变上述执行分工。
目录可以整体重命名，无需保留 `vero_v2` 名称。

技能复用 [nxp_ivesliu_skill](https://github.com/lbwlele-bot/nxp_ivesliu_skill/tree/02c4fbf16ee80a5c1732a080facacc855a588231)，
服务器访问和 Windows 工具来自原 Vero。

仓库只发布工作流、工具脚本和构建规则。RM、原理图、硬件设计文件、官方文档、
镜像、工具二进制、业务源码、SDK、固件、case 记录和本机 ENVIRONMENT 不随仓库发布，
继续保存在各自的实际资源位置。
