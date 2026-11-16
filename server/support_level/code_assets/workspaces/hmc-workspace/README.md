# hmc-workspace

这是按 NXP 正式发布 manifest 准备的 `RTE HMC` 共享源码工作区。
主 manifest 在 `heterogeneous-multicore/west.yml`，不是旧机器的目录快照。

当前保留它，是因为你关心的 `A` 核 `RTOS` / `heterogeneous-multicore`
代码不只是某一个单独仓库，而是和下面这些部分一起协同：

- `heterogeneous-multicore/`
- `zsdk/`
- `mcuxsdk/`
- `.west/`

当前本地这份 `heterogeneous-multicore` 的参考版本是：

- `Real-Time-Edge-v3.5-202607`

`mcuxsdk` 与 `zsdk` 的具体路径和提交由该正式 manifest 及其 imports 决定。
依赖按 `west update --narrow` 准备，不把所有子仓各自升级到最新，也不强制切到同名分支。
默认禁用的内部开发项目 `bifrost` 不下载、不启用。West 1.3 的全项目 freeze
会因该项目未克隆而失败；保留 resolved manifest 和已校验的活动项目提交清单。
源码、manifest 和实际提交记录见 server `work/20261110-workspace-setup/records`。


使用规则：

- 如果任务明确落到 `RTE A` 核 `RTOS`、`heterogeneous-multicore`、`west` 工作区联动，先来这里
- 如果只是查源码资产，优先回到 `../../projects/`
- 如果其实是在编纯 Zephyr，对应对象优先看 `../../../compile_targets/zephyr/`
