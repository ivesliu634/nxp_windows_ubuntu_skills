---
name: myserver
description: "从 Windows 通过已有 SSH 别名 myserver 操作 Ubuntu server。用于查源码、Git 状态、准备和修改代码、执行 Linux 构建及日志命令、SCP 收发产物；源码仓库不下载到 Windows。"
---

# Windows 到 Ubuntu server

沿用 SSH 别名 `myserver`。实际资源根、源码、SDK 和任务目录见工作区根
`ENVIRONMENT.md`，不在通用技能中写死账号、IP 或主机路径。
不重复询问服务器拓扑或密码。

## 执行位置与入口

- 源码搜索、Git、修改、下载源码、构建全部通过 SSH 在 server 完成。
- Windows 是唯一 AI 工作区，在这里维护本工作流的 Git 仓库、skills、工具、资料和主 case；
  不 clone 业务源码，不取回整棵源码和编译缓存。
- server 只是资源与执行端，不部署整套工作流、技能发现目录或 AI 入口。
  直接使用 Windows ENVIRONMENT 中的远端路径，不要求 server 存在 `workspace/AGENTS.md`、
  `.agents`、`.github` 或另一份 ENVIRONMENT。
- 远端确实需要的工具脚本单独放在 server `support_level/tools`；不为运行脚本同步整个 skill。
- Windows 资料包根的 `server/support_level` 是这些工具和构建规则的部署源，部署方式见
  [server/README.md](../../../../server/README.md)。它不代表本机有业务源码，也不用于 Windows 构建。
  更新前比较远端改动，只部署所需文件，不整树覆盖或删除远端源码、资源和 case。
- Windows case 是主目录；server 同名 case 是源码和构建现场。

## PowerShell 中执行

首次连接或排查连通性时：

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 myserver 'hostname; pwd'
```

正常做事不必每次探测。每次 SSH 都是新 shell，同一次调用中设置 cwd 和环境。
下面示例的 Linux 路径必须先按 ENVIRONMENT 替换：

```powershell
ssh myserver 'cd /absolute/server/project && git status --short && git describe --always --dirty'
```

修改前确认已有改动和版本，不覆盖用户改动。共享基线需要修改或构建时，
在 server 的任务现场准备副本。纯阅读不要求先建 case 或连接板子。

复杂 shell 命令不要依赖 PowerShell 向本机原生程序传递嵌套引号。
可以用 UTF-8 Base64 传递脚本，交给远端 bash 解析：

```powershell
$script = @'
set -e
cd "$HOME/actual-server-project"
git status --short
'@
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
ssh myserver "printf %s $encoded | base64 -d | bash"
if ($LASTEXITCODE -ne 0) { throw 'Remote command failed; keep and report the original output.' }
```

只传当前任务的命令，不把凭据放进脚本或命令参数。
Linux 的管道、变量和工具调用由 Linux 解析，不在 Windows 执行替代版本。
长构建日志留在 server；按进程退出码判断结果，不因日志暂时不增长而宣布成功。

## 取回与上传

先确认实际绝对路径；带空格的 Windows 路径必须加引号。以下路径是占位示例：

```powershell
scp 'myserver:/absolute/server/case/output.bin' 'C:\actual-root\support_level\work\case\artifacts\output.bin'
scp 'C:\actual-root\support_level\work\case\records\input.yaml' 'myserver:/absolute/server/case/input.yaml'
```

- 示例 `actual-root` 是包含 `workspace` 和 `support_level` 的资料包根，不是 `workspace` 子目录。
- server 的构建清单、配置和工具状态使用 Linux 路径；不要上传包含 Windows 路径的清单直接执行。
- 原工具生成的软件状态按原格式保留，取回的副本用于 Windows case 留存，不手改成另一份构建事实。
- 源路径与本地落地路径的对应关系记在当前 case；不混用两端同名文件。
- 镜像取回后分别执行远端 `sha256sum` 与本地 `Get-FileHash -Algorithm SHA256`。
- Linux 基线上的补丁应用检查在 server 完成；Windows 保存补丁和检查结果。

## 登录失败

- 用 `ssh -G myserver` 区分别名配置、网络/VPN、认证问题，报告原始错误。
- 新主机指纹需用户核对，不关闭正常的 SSH 主机校验。
- 密码、私钥和认证修复由用户在自己的终端处理，不写入聊天或仓库。
- 失败不循环试无关主机；缺远端工具就明确报告，不伪造本地替代执行成功。
