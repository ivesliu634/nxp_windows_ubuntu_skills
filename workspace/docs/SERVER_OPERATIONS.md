# 直接操作 server

下面是独立操作示例，按需要执行。先把示例中的路径、URL、ref 替换成这次的真实值。
AI 和 skills 只在 Windows；server 仅是 SSH 资源/执行端，不需要另一套 AI 工作区。
本工作流的 Git 在 Windows 维护，下面的远端 Git 命令只用于业务源码仓库。

## 1. 查现有源码（Windows PowerShell）

```powershell
ssh myserver 'ls -la /absolute/server/support_level'
ssh myserver 'find -H /absolute/existing/source/root -maxdepth 3 -type d -name .git'
```

定位后用真实绝对路径，例如：

```powershell
ssh myserver 'git -C /absolute/repo status --short --branch'
ssh myserver 'git -C /absolute/repo describe --tags --always --dirty'
ssh myserver 'git -C /absolute/repo remote -v'
ssh myserver 'git -C /absolute/repo grep -n "search_symbol" -- drivers arch'
```

未安装 rg 时直接 `git grep`，不为一次代码检索安装整套环境。

## 2. 获取需要修改的源码（以下在 Linux shell）

用户已有合适的工作副本时跳过本节。新任务按模块说明找到 URL，并根据目标 release 确定 ref。

```bash
mkdir -p /absolute/server/support_level/work/my-task
cd /absolute/server/support_level/work/my-task
# URL 和 TARGET_REF 是待替换文本；先查 refs 再 clone
git ls-remote --heads --tags URL
git clone --branch TARGET_REF --single-branch URL module
cd module
git status --short --branch
git rev-parse HEAD
```

`--branch` 接受分支或 tag；需要任意 commit 时，普通 clone 后在这个新副本 checkout 指定 commit。大内核仓库若只需当前版本可选择浅克隆；需要追历史时保留历史。
从本地共享仓库复制时要说明是否带入未提交改动，避免把文件复制与 Git clone 当成等价。

## 3. 修改和检查（Linux）

直接用可用编辑器或针对性脚本修改远端文件。先查看原内容，再做精确修改，最后：

```bash
git diff --check
git diff --stat
git diff
git status --short
```

需要 patch 时 `git diff --binary HEAD > ../change.patch`；它不含未跟踪的新文件，新文件另外交付，或在用户接受的情况下加入 Git 后再导出。
只让改代码的任务，到这里交付修改及位置即可。

## 4. 避免 PowerShell 与 Bash 混淆

短命令用 Windows 外层单引号。复杂多行命令可写 UTF-8 无 BOM、LF 换行的 `.sh` 文件，通过 SCP 上传，再由 Linux bash 执行。
下面只是组织方式，不自动启动编译：

```powershell
$taskDir = 'C:\actual-root\support_level\work\my-task'
$linuxText = @'
#!/usr/bin/env bash
set -euo pipefail
cd /absolute/server/task/repo
git status --short --branch
# 在这里放本次实际需要的修改或构建命令
'@
[IO.File]::WriteAllText((Join-Path $taskDir 'step.sh'), $linuxText.Replace("`r`n", "`n") + "`n", [Text.UTF8Encoding]::new($false))
scp (Join-Path $taskDir 'step.sh') 'myserver:/absolute/server/task/step.sh'
ssh myserver 'bash /absolute/server/task/step.sh'
```

先建好示例中的本地与远端任务目录。脚本是当前任务的一段普通命令，用户可读可改；简单命令无需写脚本。

## 5. 编译与手工接续

真实编译先进入 [compile](../.agents/skills/compile/SKILL.md)，再读 server 对应项目的 `USAGE.md`、清单和 policy。本地 MODULE 仅作查找线索，不替代构建规则。
原始命令仍来自项目自身的 make/cmake/west 等说明，但 Agent 统一经 server 的 `compile-tool prepare → 展示 → run` 执行；不绕过工具直接编译。用户只要手工命令时提供命令，不自行启动构建。
配置与构建分开描述，便于用户只执行其中一段。采用服务器适合的并行数，例子中的 `-j4` 可调整。

下面仅说明原生命令的日志写法，不是 Agent 绕过 `compile-tool` 的另一个入口：

```bash
set -o pipefail
make <本次实际参数> 2>&1 | tee build.log
```

如要后台长任务，先确认服务器已有 `tmux` 或 `screen` 再使用，并写明会话名和日志位置；无需为了普通编译安装后台服务。
取回文件用 SCP。只报告本次实际产生的文件；已有旧输出不能用来证明本次编译成功。
