# imx-optee-os

来源：[NXP OP-TEE](https://github.com/nxp-imx/imx-optee-os)，clone URL 为 `https://github.com/nxp-imx/imx-optee-os.git`。
Ubuntu 资料记录过 `lf-6.12.49-2.2.0`。
查平台从 `core/arch/arm/plat-imx/` 开始；`conf.mk` 中确认 flavor，原资料列过 `mx95evk`、`mx943evk`。

构建形态，所有尖括号都需替换：

```bash
make PLATFORM=imx PLATFORM_FLAVOR=<实际flavor> \
  CROSS_COMPILE=<aarch32-prefix> \
  CROSS_COMPILE64=<aarch64-prefix>
```

实际 32/64 位编译器需求、配置和输出以该版本 README 为准。
典型输出为 `out/arm-plat-imx/core/tee-raw.bin`；打包所需 `tee.bin` 可能是它的复制/转换结果，按对应 release 打包说明操作。ATF 的 dispatcher 也须对应。
