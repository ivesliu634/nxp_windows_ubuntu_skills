# 板级 SDK / FreeRTOS 发布包

先在 server 的 `m_freertos_sdk/` 或 `release_packages/m_freertos_sdk/` 找官方包。
缺包时使用对应官方 MCUXpresso SDK 发布入口或用户提供的包；需要账号/许可的步骤交给用户处理。保留压缩包，解到任务目录再改。

原 Ubuntu 资料记录过下列包，供查找，不是本版附带内容或默认版本：

| 板型线索 | 包名 | 核角色线索 |
|---|---|---|
| i.MX943 EVK | `SDK_25_09_00_IMX943-EVK.tar.gz` | cm33_core1 → m33s；cm7_core0 → m70；cm7_core1 → m71 |
| i.MX95 19x19 LPDDR5 | `SDK_26_06_00_IMX95LPD5EVK-19.zip` | cm7 → m7 |
| i.MX93 EVK | `SDK_26_03_00_MCIMX93-EVK.zip` | cm33 → m33 |

具体 SDK 是否适合目标 BSP、芯片 revision 与板型要看该包 release note。
在解包目录查 `boards/`、目标 example、README、armgcc/CMake 入口及 linker 文件。
编译使用示例随附的工具链设置和 make/cmake 命令；分别列出选核、选示例、配置、构建、输出位置，让用户手工执行。
需要 BIN 的消费端不能直接给 ELF；RAM/TCM 链接与 flash 链接不同，按加载方式选，不猜。
