# Project Compile Profile Schema（内部/兼容层）

项目自治编译对象的默认对外入口已收缩为
`COMPILE_CHECKLIST.yaml` 和 case `compile.yaml`，见
`MINIMAL_CHECKLIST_DESIGN.md`。本文的 profile、manifest、request 和
artifact 结构是 compile-tool 内核，不要求 AI 每次编译时直接维护。

项目编译模型把长期模板和当前 case 实例分开：

```text
code_assets/projects/<project>/COMPILE_PROFILE.yaml
    -> compile-tool init
work/<case>/records/compile/<project>/manifest.yaml
```

`COMPILE_PROFILE.yaml` 只描述项目稳定的生产契约，不保存 case 名、case
绝对路径、本次源码 ref 或本次参数值。生成的 manifest 才记录当前实例。

当前已启用单清单的项目：

- `imx-oei`
- `imx-atf`
- `uboot-imx`
- `real-time-edge-uboot`
- `imx-optee-os`
- `imx-sm`
- `imx-mkimage`

M SDK 不是 Git project profile，而是另一种公开清单；它仍可通过统一清单
分发层成为 project consumer 的 artifact producer。旧 `flashbin` 深度
manifest 继续兼容。已登记的 AHAB/DDR firmware 仍从 case
文件输入，记录来源并由工具观察 hash；历史 fixed-asset matrix 不再默认限制其版本。

## Profile

```yaml
schema_version: 1
id: imx-oei
type: project_compile
target: imx-oei
component: imx-oei
action: rebuild

source:
  id: imx-oei
  path: imx-oei
  case_path: sources/imx-oei
  ref_kind: tag
  remote: origin
  remote_url: https://github.com/nxp-imx/imx-oei
  update: if_missing

parameters:
  silicon_revision:
    source: user
    required: true
    pattern: '^[A-Za-z][0-9]$'
  oei_type:
    source: project
    default: ddr

configuration_parameters: [silicon_revision, oei_type]

tools:
  - name: compiler
    path: toolchain/<toolchain>/bin/arm-none-eabi-gcc
    version_args: [--version]

watched_inputs: []

outputs:
  oei_ddr:
    type: nxp.oei.ddr-image
    path: artifacts/imx-oei/oei-m33-ddr.bin
    identity_parameters: [silicon_revision, oei_type]

artifact_inputs: {}
file_inputs: {}
```

约束：

- profile 必须直接位于 `support_level/code_assets/projects/<id>/`
- `id`、`target`、`component` 和项目目录名必须相同
- source path 相对项目目录，case path、watched inputs 和 outputs 相对 case
- `required` 参数生成 `TBD`，在 manifest 进入 assess/prepare 前必须填实
- `allowed` 为可选值白名单，`pattern` 是全值正则；两者由工具强制
- `configuration_parameters` 自动进入组件配置指纹
- output 同时定义可被下游引用的具名 artifact
- `action` 定义项目执行语义：源码项目为 `rebuild`，mkimage 为 `repack`
- `file_inputs` 定义 checklist 允许的固定文件 slot 及是否允许多个
- 硬门禁继续由同项目目录的 `COMPILE_POLICY.yaml` 负责

## Checklist Build Contract

AI 不在 case 清单中填 shell 命令。项目 profile 通过固定 token
模板描述真实命令：

```yaml
checklist_build:
  mode: isolated_git
  env:
    CROSS_COMPILE: ${tool_prefix.compiler}
  steps:
    - name: build-imx-atf
      command:
        - /usr/bin/env
        - -u
        - LDFLAGS
        - ${tools.make}
        - PLAT=${parameters.platform}
        - value: SPD=${parameters.spd}
          omit_when: {parameter: spd, equals: none}
        - bl31
```

profile 加载时会校验参数、tool 引用和可选 token 条件。
case 清单只能选 profile 允许的参数和工具路径；compile-tool 再把
token 安全渲染为 prepare 报告中的原始命令。`build` 字段只保留
`mode: isolated_git`，增加 `command` 或 `env` 会直接被拒绝。

## Project Input Rules

consumer 可以在 profile 内声明不依赖 recipe 名称的通用输入规则，例如：

```yaml
input_contract:
  artifacts:
    atf:
      slot: atf
      stage_pattern: '^.+$'
      producer_parameters:
        platform: ${parameters.soc}
  extra_file_slots:
    firmware: {stage_pattern: '^.+$'}

make_recipe_inputs:
  soc_parameter: soc
  recipe_parameter: recipe
  m_payload_slot: m_payload
  soc_identity_overrides: {iMX94: imx943}
```

这些规则绑定 profile hash。mkimage 检查已声明的非 M 输入角色和 OP-TEE/ATF
`SPD=opteed` 等关系，但不按历史 recipe 清单决定能力上限。落位仍必须是 case
执行副本内的安全相对路径；Agent 根据当前源码明确哪些输入必需、应放到哪里。
`producer_parameters` 可以用 `${parameters.<name>}` 绑定当前参数。
固定文件的公开清单条目支持 `provenance`；mkimage 要求该字段非空且不是占位值，
工具将其写入配置指纹并展示实际文件 hash。

`make_recipe_inputs` 让工具从选定源码 ref 的 `<SOC>/soc.mak` 安全读取 target
依赖，不执行 Make recipe，并自动得出 M payload 文件名。M producer 的类型仍由
artifact slot 约束，SoC/core role 由文件名和少量无法从 Makefile 表达的 SoC
identity override 补充；解析结果和 `soc.mak` hash 进入组件配置指纹。

文件型 `input_contract: {path, selectors}` 和 `fixed_asset_contract`
仍可表达某个项目明确选定的版本约束，保留其 hash、role、slot、落位及 SHA-256 检查。
它们不是所有项目的必填项；mkimage 默认不再绑定历史组合矩阵。
固定文件的当前 hash 不证明发布兼容性；prepare/run 绑定只能证明执行使用同一份输入。

## Init

```bash
compile-tool init imx-oei \
  --case-root /absolute/work/<case> \
  --ref lf-6.18.2-1.0.0 \
  --set silicon_revision=B0 \
  --set board=mx95lp5
```

生成位置：

```text
work/<case>/records/compile/imx-oei/manifest.yaml
```

如果未给出 required 参数或 ref，工具仍生成 draft，但后续 manifest 校验会
阻断。已有 manifest 不会被覆盖。

生成的 manifest 绑定：

```yaml
project_profile:
  path: /absolute/.../COMPILE_PROFILE.yaml
  hash: sha256:<profile-identity>
```

profile 改变后，旧实例必须重新生成，不能静默继承新模板。

## Artifact Export

producer manifest 显式导出：

```yaml
exports:
  oei_ddr:
    component: imx-oei
    type: nxp.oei.ddr-image
    path: /absolute/case/artifacts/imx-oei/oei-m33-ddr.bin
    identity_parameters: [silicon_revision, board, oei_type]
```

成功状态记录对应 component 的源码、配置、工具和 output SHA-256。export
本身不表示文件已经有效；只有 producer 成功状态存在且当前文件 hash 与该
状态一致时，下游才能消费。

## Artifact Input Contract

consumer profile 定义允许的输入槽位：

```yaml
artifact_inputs:
  oei:
    type: nxp.oei.ddr-image
    multiple: false
    required_when:
      parameter: oei_enabled
      equals: 'YES'
    parameter_matches:
      silicon_revision: silicon_revision
  m_payload:
    type: nxp.mcore.bin
    multiple: true
    parameter_matches:
      soc: soc
```

case manifest 选择实际 producer：

```yaml
artifact_inputs:
  oei_image:
    slot: oei
    manifest: /absolute/case/records/compile/imx-oei/manifest.yaml
    artifact: oei_ddr
```

工具检查：

- producer 和 consumer 必须属于同一个 case
- 不能引用自身 target
- slot 必须由 consumer profile 声明
- 非 multiple slot 不能选择多个输入
- `required_when` 命中时必须选择输入
- producer manifest/profile hash 必须与最后成功状态一致
- producer component 必须有成功状态
- artifact path/type/export 必须匹配
- 当前 artifact SHA-256 必须和 producer 成功状态一致
- `parameter_matches` 指定的身份参数必须一致
- M producer 还必须匹配 recipe contract 固定的 `core_role`；ELF 类型不会被
  BIN slot 接受

consumer 状态记录 producer state identity、artifact SHA-256、type 和 identity。
producer 成功状态或 artifact 变化后，consumer assessment 自动失效。

## Dependency Direction

项目依赖使用 producer/consumer 语义：

```text
imx-oei --exports--> oei_ddr --consumed by--> imx-mkimage
```

不要把它写成 `imx-oei depends_on flashbin`。OEI 可以独立构建；最终
`flash.bin` 是否选择 OEI、M payload、OP-TEE 等，由 imx-mkimage 当前 case
manifest 和 recipe 参数决定。

## Current Boundary

- 每个 request 仍只执行一个 manifest/target
- 一个 consumer checklist 可以递归 materialize 其显式引用的 producer
  checklist；producer 可以是 Git project checklist 或 M SDK checklist，但
  工具不会自己猜应该选哪个 producer、job 或 recipe
- 当前只有项目 profile 的 generic schema v2 manifest 可以声明
  `artifact_inputs`
- artifact contract 证明生产者成功状态与内容身份，不证明 Makefile 内部如何
  消费该文件，也不证明最终镜像能在板上运行
- 历史 recipe/fixed-asset 矩阵保留已整理组合及包版本，不构成 mkimage 的能力上限；
  新组合仍须根据当前源码和发布资料核对，不能把工具通过当作兼容性证明
- 源码要求的 M payload 必须来自 M SDK producer；公共 mkimage 清单不接受裸 M 文件
- 旧 flashbin schema v1 和 `records/compile-manifest.yaml` 尚未删除
