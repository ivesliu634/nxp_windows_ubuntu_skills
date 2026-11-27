---
name: compile
description: 在 Ubuntu server 准备 NXP 产物或镜像，分析构建目标、最小依赖和输入，执行 build、make、cmake、west、bitbake 或交叉编译，并核对构建记录与待上板产物。
---

# 构建与产物准备

通过 `ssh myserver` 在 Ubuntu server 分析依赖、准备输入并执行构建计划。
具体项目命令和版本要求按对应项目的 USAGE、清单与 policy 核对。

## 两端执行适配

- 下文源码、SDK、构建对象、`compile-tool` 和其清单路径均指 server。
  server 实际根从 ENVIRONMENT 解析，不能把 Windows 相对路径送给 server。
  Windows 的 `../support_level` 是 workspace 同级资源层。
- 命令、环境变量和 cwd 在同一次 SSH 中设置；继续使用项目原生命令与参考系统已有的输入校验。
- server 已单独部署原 `compile-tool`、项目清单、policy、构建对象及软件栈说明，
  实际根见 ENVIRONMENT。工具帮助可用不代表具体任务的源码、SDK、工具链和固定固件已齐备；
  缺输入时明确报告，不擅自用其他版本替代，也不为部署工作流启动实际构建。
- 本 skill 只在 Windows 加载；经 `myserver` 读取远端项目说明并调用构建工具。
  server 不需要 AI 工作区、skill 副本或工作流 Git 仓库。
  Windows 资料包根的 `server/support_level` 是这些小文件的维护/部署源，不是本机编译入口。
- Windows 主 case 为 `..\support_level\work\<case>`（相对于 workspace）；server 同名 case 保存源码和构建现场。
  构建清单在 server 使用 Linux 路径，工具生成的记录、软件状态、补丁和所需产物按需取回。
- `software-state` 不手改。远端产物路径与 Windows 落地路径在 case 中分开记录，
  取回后核对大小和 SHA-256，确认后才可用于板级动作。
- 所有 Linux 构建和业务源码 Git 操作都经 SSH；工作流自身的 Git 操作在 Windows。
  用户仅要代码修改或命令说明时不自行构建。

---

## 先判断运行链路和编译对象

第一步不是跑命令，而是先理运行链路：

1. 哪些 CPU / 固件阶段会参与运行
2. 它们的先后关系和依赖关系是什么
3. 为让这条链路成立，最小需要准备哪些依赖
4. 哪些共享基线或固定输入可以直接使用，哪些必须重编

不要一上来就编整套；先收敛最小依赖集合。
也不要默认复用旧 `work/` 里的产物；
除非已经非常清楚那些产物的来源、版本、配置和生成过程都可控，
否则按需要重建，或回到共享基线重新出产物。

### 常见编译对象

- `flashbin`
- `linux`
- `m_freertos_sdk`
- `zephyr`
- `a55_rtos`

### 进入编译对象前必须钉死的守门项

- 当前软件栈 / 版本分支
- 打包目标
- 最终期望产物类别
- 工具链归属划分

这些字段属于跨项目构建身份。
如果这里没钉死，后面就不要让具体对象开始编。

如果当前软件栈是 `RTE 3.3`、`RTE 3.4`、`Real-Time Edge`
这类跨项目软件线，先进入
`support_level/software_stacks/rte.md`。
不要直接跳到 `imx-atf`、`imx-sm`、`U-Boot` 或 `linux`
单个项目文档里推断整条 RTE 链路。

## 统一编译执行入口

源码阅读、依赖分析、编译对象判断和命令规划不需要调用工具。
只有准备进入真实编译或软件状态评估时，才进入：

- `../support_level/tools/compile-tool/USAGE.md`
- `../support_level/tools/compile-tool/compile-tool`

### flashbin

OEI、ATF、U-Boot、OP-TEE、SMFW 和 imx-mkimage 使用项目清单入口。
每个项目一张清单，不要求 Agent 另填工具内部 manifest/request：

```text
records/compile/imx-oei/compile.yaml
records/compile/imx-atf/compile.yaml
records/compile/uboot-imx/compile.yaml
records/compile/imx-optee-os/compile.yaml
records/compile/imx-sm/compile.yaml
records/compile/imx-mkimage/compile.yaml
records/compile/m_freertos_sdk/compile.yaml
```

从项目 `COMPILE_CHECKLIST.yaml` 复制并填写，然后只执行
`prepare <compile.yaml> -> run <compile.yaml>`。profile、manifest、assessment 和 request
是工具内部实现，不由 AI 维护。producer 成功后，consumer 清单通过
同 case `checklist + artifact` 引用其具名产物。工具校验 producer 成功
状态、hash、type 和身份参数。imx-mkimage 的实际输入由当前源码、项目说明和
本次目标确定，工具检查所声明的输入，不把上游项目的编译规则重新塞回 mkimage。

该模型当前没有自动跨 manifest 编排，必须显式先 producer、后 consumer。
mkimage 不按历史 recipe 或固件矩阵限定可编组合。Agent 必须核对当前源码的
recipe、完整输入及发布版本；固定文件须填写 `provenance`，工具观察 hash 并绑定
prepare/run。M payload 通过 M SDK 公共清单引用其 `nxp.mcore.bin`。
SCFW 尚无独立公开清单，需要已有整链路请求的场景仍可使用下述接口。

#### 整链路请求入口（仅限明确使用 `target: flashbin` 的任务）

这一接口由 Agent 显式维护整条链的 manifest/request。
它与上面的项目清单是两种输入形式，不是同一次任务必须重复填写的两套表。
项目清单已经由工具生成内部记录时，不再额外填写以下文件。

仅在使用整链路请求入口时，在当前 case 准备：

- `records/compile-manifest.yaml`
- `records/compile-request.yaml`

manifest 必须按 `compile-tool/SOFTWARE_STATE_SCHEMA.md`
覆盖 dependency profile 中的全部候选组件；
未使用组件填写 `not_applicable + reason`。

流程固定为：

1. 执行 `compile-tool requirements <manifest>`，确认当前 component
   触发的受约束参数清单
2. 执行 `compile-tool assess <manifest>`
3. 如果是 `ACQUIRE_REQUIRED`，完整展示源码准备命令，
   再以同一 hash 执行 `compile-tool acquire`
4. 重新 `assess`，读取 `MATCHED / CHANGES_OBSERVED` 状态摘要
5. 由 LLM 根据任务目标和工程判断决定是否重编，并在 schema v2 request
   的 `decision.scope/reason` 中声明直接变更组件和理由
6. 请求按 `compile-tool/REQUEST_SCHEMA.md` 绑定 manifest 和 assessment；
   unit 只能位于 scope 或其显式下游
7. 执行 `compile-tool prepare <request>`
8. 在 commentary 中向用户完整展示 `prepare` 输出的受约束参数、
   assessment、LLM 决策范围、工作目录、环境变量和原始命令
9. 无需逐次等待用户确认，执行 `compile-tool run <request>`

`state/software-state.yaml` 只能由工具生成。
不要手工填写 hash、把失败产物标成成功，或绕过 decision scope
增加无关平级组件。

managed Git 的 case source 只承载源码身份。普通 out-of-tree 构建的 cwd
必须位于源码树外；命中 `isolated_git` policy 的 in-tree component 必须使用
compile-tool 显示的 `build/.compile-tool/<target>/<component>/source/`。
不要通过 `.gitignore` 或 manifest 生成路径白名单隐藏构建生成物。

只要源码、配置、工具链、产物、依赖图或受约束参数发生变化，
旧 assessment hash 就失效；必须重新 assessment 和 prepare。

不要全局要求 SoC、silicon revision、封装、板型、DDR 和软件版本。
参数是否允许 assumption/default，或者必须询问用户，
以 compile target、源码项目或 workspace 旁边的 `COMPILE_POLICY.yaml`
为机器权威。

当前 OEI 和 imx-mkimage/flashbin 的 `silicon_revision`
是 `must_ask_user`：不知道就停下来问用户；
manifest 中必须记录 `source: user`，对应 make 命令必须显式包含同值
`REV=<value>`，不能依赖项目默认值。

SMFW rebuild 还必须声明 `smfw_config`，并按 policy 执行：
删除 `configs/<smfw_config>/` 生成目录、`make really-clean`、
`make config=<smfw_config> cfg`、`make config=<smfw_config> all`。
不能删除 `.cfg` 源文件或整个 `configs/`。

### M SDK 公共清单与其他 compile target

M FreeRTOS 已使用独立公共清单：

- 模板：`../support_level/compile_targets/m_freertos_sdk/COMPILE_CHECKLIST.yaml`
- case：`records/compile/m_freertos_sdk/compile.yaml`
- 一张清单可含多个具名 job；每个 job 独立状态
- AI 只填 package/compiler/job/intent，不填 backend、命令、输出路径或内部请求
- source build 同源发布 ELF+BIN；prebuilt import 只校验、复制和发布

Linux、Zephyr、A55 RTOS 和后续普通 target
使用通用 schema v2 状态单元，在当前 case 准备：

- `records/compile/<target>/manifest.yaml`
- `records/compile/<target>/request.yaml`

`target: linux` 是窄化的长构建例外：`run` 将编译 stdout/stderr
完整写入 case 的 `logs/compile/linux/`，以进程退出判定结束，
成功只返回耗时与日志路径，失败才返回受限摘要。
不要在外层反复读取该日志判断进度。这个例外不传播到
Zephyr、A55 RTOS、flashbin 或 M SDK。

调用流程仍是 `assess -> 必要时 acquire -> prepare -> run`。
manifest 只列本次实际需要的 component、明确来源、配置、工具、
watched inputs、产物和已知依赖。工具只传播 manifest 明确写出的
`depends_on`，不补猜未知依赖。imx-mkimage 是一个窄例外：工具只读取选定
ref 的 `soc.mak` target 依赖以得到 M payload 文件名，不执行 Make recipe；
普通 target 仍不解析 Makefile、Kbuild 或 west manifest。

普通通用状态单元只能使用 `rebuild`；公开清单生成的受控预编译单元可使用
`import`。文件级增量和 `west build` 是否使用
`-p always` 仍由项目手册和工程判断决定。普通组件使用 clean、mrproper、
really-clean 或递归强制删除时，必须在 request 中显式说明 destructive 理由。
新增普通 target 默认只增加 manifest，不为它新增 Python profile。

schema v1 只保留给尚未纳入软件状态维护的临时命令；
它只做请求形状和原始命令校验，不更新 `software-state.yaml`，
也不应用 component 参数规则。

在本工作区的规范流程中，
不直接执行裸 `make`、`cmake`、`ninja`、`bitbake`
或其它真实编译命令。
这些原始命令仍由当前 compile target、项目 `USAGE.md`
和工程判断决定，`compile-tool` 只负责显式展示、绑定和执行，
不生成 recipe；前述 imx-mkimage `soc.mak` 依赖读取不改变这一边界。

## 查阅相关项目资料

按本次问题读取需要的说明，不要求逐层遍历：

- 软件栈身份与跨项目版本组合：server `support_level/software_stacks/<stack>.md`。
- 编译对象及候选依赖：server `support_level/compile_targets/<target>/README.md`。
- 项目命令、输入输出与版本要求：server `support_level/code_assets/projects/<project>/USAGE.md`。
- 协同工作区约束：server `support_level/code_assets/workspaces/<workspace>/README.md`。
- 板 revision、板级基线与风险：Windows `..\support_level\board_knowledge\README.md` 及其索引，
  不在 server 查同名目录，也不把历史 Linux 操作当成当前 Windows 命令。

已有 `RELATION.yaml` 可帮助定位关联资源、case 要求和 warning；
具体构建命令及版本契约仍以项目说明、清单和 policy 为准。

### 共享基线 vs case 构建

- 共享基线原则上保持可还原
- 源码浏览、版本核对，以及可逆的 checkout / tag / branch 切换，可以直接在共享基线里做
- 只要要改、要编、要生成输出，就进 `../support_level/work/<case>/`
- `../support_level/work/<case>/` 是当前 case 的构建和临时产物目录，不应默认拿旧 case 产物继续复用

特别注意：

- 不要因为某个 workspace 里带着 `zephyr/` 或 `mcuxsdk/`
  就默认从那里开始编
- 对 `a55_rtos`，`heterogeneous-multicore` 是主对象；
  同工作区里的 `zsdk/`、`mcuxsdk/` 只是联动输入
- 对 `zephyr`，不要默认从 `hmc-workspace/zsdk/` 开始

## 待上板产物记录

任务已明确需要上板，且已形成可用于板级操作的产物集合时，
在当前 case 下生成或更新 `handoff`。它是产物与消费方式的记录，不表示板子已执行任何动作。

站在当前 `workspace/` 视角，
默认落点是：

- Windows 主 case：`../support_level/work/<case>/state/handoff.yaml`
- server 构建现场：ENVIRONMENT 中的同名 case；按需取回工具生成的构建记录和所需产物，
  在 Windows 主 case 写 handoff，不直接把远端状态文件中的 Linux 路径当作本地路径。

### 什么时候需要 `handoff`

需要的场景是：

- 当前任务不止于“本地产物准备”
- 下一步已经明确要上板
- 后续上板动作不能只靠对话上下文维持

不需要的场景是：

- 只是分析编译链路
- 只是确认依赖集合
- 只是本地编译但还没进入板级执行

### 记录范围

按实际产物与构建证据记录：

- 这次作为一个完整部署组合交付的产物是什么
- 每个产物从哪来、放在哪、大小和 hash 是什么
- 顶层写入产物的消费方式和目标路径
- M 核、SCFW、BL31 等组件是否已经嵌入某个顶层 boot image
- 预期交给哪个执行阶段去消费
- 上板前提里，哪些是编译阶段已经明确知道的
- 上板后优先验证什么

不能仅凭产物准备情况填写：

- 板当前实际运行到哪一步
- 板当前允许做什么动作
- 板已经成功进入下一阶段

### 最小 `handoff` 模板

第一阶段不追求重 schema，
但最小模板至少要能表达：

- `producer`
- `artifacts`：`server_path`、`windows_path`、`size_bytes`、`sha256`
- `consumption`：顶层产物的写入方式/目标，以及组件的 `embedded_in` 关系
- `target_step`
- `preconditions`
- `verification_focus`

顶层待写入产物必须同时记录 server 原始路径与 Windows 落地路径，例如：

```yaml
artifacts:
  - name: flash.bin
    server_path: /absolute/server/support_level/work/case/artifacts/flash.bin
    windows_path: 'C:\actual-root\support_level\work\case\artifacts\flash.bin'
    size_bytes: 123456
    sha256: REPLACE_WITH_64_HEX_SHA256
```

示例路径、大小和 hash 都必须替换为本次事实。SCP 后分别核对两端实际字节数和 SHA-256；
只有大小及 hash 一致才可用于板级动作。尚未取回、校验失败或字段仍是占位值时，
明确记录为待完成，不能称为可上板产物。Windows 工具只消费 `windows_path`，
`server_path` 只用于来源和传输，不改写工具生成的 `software-state`。
仅作为 `embedded_in` 来源记录、不会单独写入的组件无需为了补字段而下载，
保留其 server 路径和组件身份即可，不虚构 Windows 路径。

同一个 `handoff` 中列出的顶层写入产物构成一套部署组合。
不能把其中某个 `flash.bin`、Image、DTB 或 module
静默替换成其它实验版本。

默认不再单独创建重复的 `deployment.yaml`；
部署组合仍由现有 `state/handoff.yaml` 表达。
