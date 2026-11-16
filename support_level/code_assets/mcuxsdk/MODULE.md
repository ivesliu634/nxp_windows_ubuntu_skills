# MCUX SDK 源码与 manifest

- 外设驱动与 SDK 核心：[mcuxsdk-core](https://github.com/nxp-mcuxpresso/mcuxsdk-core)，clone URL `https://github.com/nxp-mcuxpresso/mcuxsdk-core.git`。
- 组成 workspace 的 manifest：[mcuxsdk-manifests](https://github.com/nxp-mcuxpresso/mcuxsdk-manifests)，clone URL `https://github.com/nxp-mcuxpresso/mcuxsdk-manifests.git`。

查外设实现可从 core 的 `drivers/`、`devices/` 及对应 SoC 目录开始；具体目录由当前 ref 决定。
core 适合源码查阅，不等同于完整可构建的板级 release SDK。目标为已有 SDK 示例时优先 [m_freertos_sdk](../m_freertos_sdk/MODULE.md)。
确实需要 west workspace 时，使用所选 manifest 版本 README 的 `west init` / `west update` 步骤，在 server 任务目录完成，并保留原 manifest 版本。不要为普通驱动查询先下载整个 workspace。
