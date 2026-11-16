# imx-sm（System Manager）

来源：[NXP System Manager](https://github.com/nxp-imx/imx-sm)，clone URL 为 `https://github.com/nxp-imx/imx-sm.git`。
Ubuntu 资料记录过 `lf-6.18.2-1.0.0`。查配置从 `configs/` 和仓库 README 开始。
配置线索：`mx94evk.cfg`、`mx95evk.cfg`、`other/mx95rte.cfg`，按板型与软件线确认。

在新的任务工作副本中，先按仓库要求设置 `arm-none-eabi` 工具链路径，再分步：

```bash
export SM_CROSS_COMPILE=/absolute/toolchain/bin/arm-none-eabi-
make SM_CROSS_COMPILE="$SM_CROSS_COMPILE" config=<实际配置名> cfg
make SM_CROSS_COMPILE="$SM_CROSS_COMPILE" config=<实际配置名> all
```

典型输出 `build/<config>/m33_image.bin`。
复用旧构建目录并修改配置时，`make really-clean` 可能仍留下 `configs/<config>/` 生成目录。先核对它确为可再生输出且没有手工改动，再清理该生成目录、执行 `make really-clean`、重新 cfg 与 all。原始 `configs/<config>.cfg` 要保留。
RTE 场景只应用 SMFW 对应 patch，配置以该 release 的说明为准。
